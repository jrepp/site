/* Public, unauthenticated GitHub data only. The rendered snapshot is the fallback. */
(async () => {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const get = async path => {
      const response = await fetch(`https://api.github.com/${path}`, {signal: controller.signal, headers: {Accept: 'application/vnd.github+json'}});
      if (!response.ok) throw new Error('GitHub unavailable');
      return response.json();
    };
    const user = await get('users/jrepp');
    if (user.login !== 'jrepp' || !Number.isInteger(user.public_repos) || !Number.isInteger(user.followers)) throw new Error('Invalid profile');
    document.getElementById('repo-count').textContent = user.public_repos;
    document.getElementById('follower-count').textContent = user.followers;
    if (user.location) document.getElementById('location').textContent = user.location;
    document.getElementById('github-status').textContent = 'GitHub profile refreshed · ' + new Date().toLocaleDateString(undefined, {month: 'short', day: 'numeric', year: 'numeric'});
    // Fetch each selected public project so selection never depends on pagination.
    await Promise.allSettled([...document.querySelectorAll('[data-stars]')].map(async element => {
      const repo = await get('repos/jrepp/' + encodeURIComponent(element.dataset.stars));
      if (repo.private !== false || !Number.isInteger(repo.stargazers_count)) return;
      element.textContent = '☆ ' + repo.stargazers_count;
      const card = element.closest('.project');
      if (repo.description) card.querySelector('p').textContent = repo.description;
      if (repo.language) card.querySelector('.project-meta > span').textContent = repo.language;
    }));
  } catch (_) {
    // Keep the dated, server-rendered snapshot when offline or rate limited.
  } finally {
    clearTimeout(timeout);
  }
})();
