const fs = require('fs');
const { Octokit } = require('@octokit/rest');

const token = process.env.GITHUB_TOKEN;
if (!token) throw new Error('GITHUB_TOKEN required');
const octokit = new Octokit({ auth: token });

const repoFull = process.env.GITHUB_REPOSITORY || `${process.env.GITHUB_ACTOR}/${process.env.GITHUB_ACTOR}`;
const owner = repoFull.split('/')[0];

const aiTopics = (process.env.AI_TOPICS || 'ai,machine-learning,deep-learning,artificial-intelligence').split(',').map(s=>s.trim());
const testTopics = (process.env.TEST_TOPICS || 'testing,test-automation,qa,unit-testing').split(',').map(s=>s.trim());

async function searchTop(topics) {
  // Build search query: topic:A OR topic:B ...
  const q = topics.map(t => `topic:${t}`).join('+OR+');
  const res = await octokit.request('GET /search/repositories', {
    q: `${q}+is:public`,
    sort: 'stars',
    order: 'desc',
    per_page: 20
  });
  return (res.data.items || []).slice(0, 10).map(r => ({
    full_name: r.full_name,
    html_url: r.html_url,
    description: r.description,
    stars: r.stargazers_count,
    language: r.language,
    topics: r.topics || []
  }));
}

(async () => {
  try {
    const ai = await searchTop(aiTopics);
    const testing = await searchTop(testTopics);

    const out = {
      generated_at: new Date().toISOString(),
      ai,
      testing
    };

    if (!fs.existsSync('data')) fs.mkdirSync('data');
    fs.writeFileSync('data/top_repos.json', JSON.stringify(out, null, 2));

    // Insert or update a README section between the markers <!--TOP_REPOS_BEGIN--> and <!--TOP_REPOS_END-->
    const readmePath = './README.md';
    let readme = fs.existsSync(readmePath) ? fs.readFileSync(readmePath,'utf8') : `# ${owner}\n\n`;

    const formatList = (arr) => arr.map((r,i) => `${i+1}. [${r.full_name}](${r.html_url}) — ${r.stars} ★ — ${r.language || '—'}\n\n${r.description || ''}`).join('\n\n');

    const mdSection = `<!--TOP_REPOS_BEGIN-->\n\n## 每日 Top 仓库（AI）\n\n${formatList(ai)}\n\n## 每日 Top 仓库（Testing）\n\n${formatList(testing)}\n\n<!--TOP_REPOS_END-->`;

    if (readme.includes('<!--TOP_REPOS_BEGIN-->')) {
      readme = readme.replace(/<!--TOP_REPOS_BEGIN-->[\s\S]*<!--TOP_REPOS_END-->/, mdSection);
    } else {
      readme += '\n\n' + mdSection;
    }
    fs.writeFileSync(readmePath, readme, 'utf8');

    console.log('Wrote data/top_repos.json and updated README');
  } catch (err) {
    console.error('Error generating top repos:', err);
    process.exit(1);
  }
})();
