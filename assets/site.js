const filters = document.querySelector('[data-filter]');
if (filters) {
  const search = filters.querySelector('#search');
  const category = filters.querySelector('#category');
  const stories = [...document.querySelectorAll('.story')];
  const normalized = value => value.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');
  const indexed = stories.map(story => {
    const content = [...story.querySelectorAll('h2, .script, .selection dd, .follow-up, .sources')];
    return { story, content, text: normalized(content.map(part => part.textContent).join(' ')) };
  });
  const highlight = (story, content, pattern) => {
    for (const mark of story.querySelectorAll('mark[data-episode-match]')) {
      mark.replaceWith(document.createTextNode(mark.textContent));
    }
    story.normalize();
    if (!pattern) return;
    for (const part of content) {
      const walker = document.createTreeWalker(part, NodeFilter.SHOW_TEXT);
      const nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);
      for (const node of nodes) {
        const matches = [...node.data.matchAll(pattern)];
        if (!matches.length) continue;
        const fragment = document.createDocumentFragment();
        let start = 0;
        for (const match of matches) {
          fragment.append(node.data.slice(start, match.index));
          const mark = document.createElement('mark');
          mark.dataset.episodeMatch = '';
          mark.textContent = match[0];
          fragment.append(mark);
          start = match.index + match[0].length;
        }
        fragment.append(node.data.slice(start));
        node.replaceWith(fragment);
      }
    }
  };
  const update = () => {
    const hasQuery = Boolean(search.value.trim());
    const terms = [...new Set(search.value.trim().split(/\s+/).map(normalized).filter(Boolean))];
    // Normalized terms contain only letters/numbers. Allow punctuation and
    // spacing between those characters so BooBench also highlights Boo Bench.
    const pattern = terms.length ? new RegExp(terms.sort((a, b) => b.length - a.length)
      .map(term => [...term].join('[^\\p{L}\\p{N}]*')).join('|'), 'giu') : null;
    let count = 0;
    for (const { story, content, text } of indexed) {
      const visible = (!hasQuery || (terms.length > 0 && terms.every(term => text.includes(term)))) &&
        (!category.value || story.dataset.category === category.value);
      story.hidden = !visible;
      highlight(story, content, visible ? pattern : null);
      count += Number(visible);
    }
    for (const note of document.querySelectorAll('.stories .sponsor-note')) {
      note.hidden = hasQuery || Boolean(category.value);
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
  search.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      event.preventDefault();
      filters.reset();
    }
  });
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
