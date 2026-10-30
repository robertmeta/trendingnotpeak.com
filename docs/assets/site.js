const filters = document.querySelector('[data-filter]');
if (filters) {
  const search = document.querySelector('#search');
  const category = document.querySelector('#category');
  const stories = [...document.querySelectorAll('.story')];
  const normalized = value => value.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');
  const update = () => {
    const query = normalized(search.value);
    let count = 0;
    for (const story of stories) {
      const visible = normalized(story.textContent).includes(query) &&
        (!category.value || story.dataset.category === category.value);
      story.hidden = !visible;
      count += Number(visible);
    }
    document.querySelector('#result-count').textContent = `${count} of ${stories.length} stories`;
    document.querySelector('.empty').hidden = count !== 0;
  };
  const revealLink = (hash = location.hash) => {
    if (!hash) return;
    const story = stories.find(item => `#${item.id}` === hash || `#${item.dataset.storyId}` === hash);
    if (story?.hidden) {
      filters.reset();
      update();
      story.scrollIntoView();
    }
  };
  filters.hidden = false;
  filters.addEventListener('input', update);
  filters.addEventListener('submit', event => event.preventDefault());
  filters.addEventListener('reset', () => { search.value = ''; category.value = ''; update(); });
  window.addEventListener('hashchange', () => revealLink());
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#"]');
    if (link) revealLink(link.getAttribute('href'));
  });
  update();
  revealLink();
}

const siteSearch = document.querySelector('[data-site-search]');
if (siteSearch) {
  siteSearch.addEventListener('submit', event => {
    event.preventDefault();
    const query = siteSearch.elements.q.value.trim();
    if (!query) return;
    const url = new URL(siteSearch.action);
    url.searchParams.set('q', `${query} site:trendingnotpeak.com`);
    location.assign(url.href);
  });
}
