// Static adaptation of dqnamo's Kitchen Cassette Audio Player.
// https://www.dqnamo.com/experiments/cassette-player
for (const player of document.querySelectorAll('[data-cassette]')) {
  const audio = player.querySelector('audio');
  const cassette = player.querySelector('.cassette');
  const play = player.querySelector('[data-play]');
  const restart = player.querySelector('[data-restart]');
  const mute = player.querySelector('[data-mute]');
  const seek = player.querySelector('#episode-seek');
  const volume = player.querySelector('#episode-volume');
  const speed = player.querySelector('#episode-speed');
  const error = player.querySelector('.cassette-error');
  const preference = (key, value) => {
    try {
      if (value === undefined) return localStorage.getItem(key);
      localStorage.setItem(key, value);
    } catch (error) { console.debug('Player preference storage unavailable', error.name); }
  };
  const savedSpeed = preference('tnp-playback-rate');
  if ([...speed.options].some(option => option.value === savedSpeed)) speed.value = savedSpeed;
  const applySpeed = () => {
    audio.defaultPlaybackRate = Number(speed.value);
    audio.playbackRate = Number(speed.value);
    audio.preservesPitch = true;
  };
  const time = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
  let frame;
  const showError = message => { error.textContent = message; error.hidden = false; };
  const update = () => {
    const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
    seek.disabled = !duration;
    seek.max = duration || 1;
    seek.value = audio.currentTime;
    seek.setAttribute('aria-valuetext', `${time(audio.currentTime)} of ${time(duration)}`);
    player.querySelector('[data-elapsed]').textContent = time(audio.currentTime);
    player.querySelector('[data-duration]').textContent = time(duration);
    restart.disabled = audio.currentTime <= 0;
    const progress = duration ? audio.currentTime / duration : 0;
    cassette.style.setProperty('--left-tape', 1 - progress * 0.4);
    cassette.style.setProperty('--right-tape', 0.6 + progress * 0.4);
    // Match Kitchen: playback itself drives the reels, with no separate opt-in.
    cassette.style.setProperty('--rotation', `${(audio.currentTime * 300) % 360}deg`);
  };
  const animate = () => { update(); if (!audio.paused) frame = requestAnimationFrame(animate); };
  const updatePlayback = () => {
    play.setAttribute('aria-label', audio.paused ? 'Play episode' : 'Pause episode');
    play.firstElementChild.textContent = audio.paused ? '▶' : 'Ⅱ';
    cancelAnimationFrame(frame);
    if (!audio.paused) frame = requestAnimationFrame(animate);
    update();
  };
  play.addEventListener('click', async () => {
    if (!audio.paused) { audio.pause(); return; }
    error.hidden = true;
    // A failed <source> selection needs a fresh load before a listener can retry.
    if (audio.networkState === HTMLMediaElement.NETWORK_NO_SOURCE) audio.load();
    try { await audio.play(); }
    catch { showError('Playback could not start. Press play to retry, or download the MP3 below.'); }
    updatePlayback();
  });
  restart.addEventListener('click', () => { audio.currentTime = 0; update(); });
  seek.addEventListener('input', () => { audio.currentTime = Number(seek.value); update(); });
  volume.addEventListener('input', () => { audio.volume = Number(volume.value); audio.muted = false; });
  speed.addEventListener('change', () => {
    applySpeed();
    preference('tnp-playback-rate', speed.value);
  });
  mute.addEventListener('click', () => {
    if (audio.muted || audio.volume === 0) { audio.muted = false; if (!audio.volume) audio.volume = 0.78; }
    else audio.muted = true;
  });
  audio.addEventListener('volumechange', () => {
    const muted = audio.muted || audio.volume === 0;
    mute.setAttribute('aria-label', muted ? 'Unmute' : 'Mute');
    mute.firstElementChild.textContent = muted ? '×' : '♪';
    volume.value = audio.muted ? 0 : audio.volume;
  });
  for (const event of ['loadedmetadata', 'durationchange', 'timeupdate', 'seeked']) audio.addEventListener(event, update);
  for (const event of ['play', 'pause', 'ended']) audio.addEventListener(event, updatePlayback);
  const loadError = () => showError('This audio could not load. Check your connection and try the MP3 link below.');
  audio.addEventListener('error', loadError);
  audio.querySelector('source')?.addEventListener('error', loadError);
  audio.addEventListener('playing', () => { error.hidden = true; });
  audio.addEventListener('loadedmetadata', applySpeed);
  applySpeed();
  audio.volume = Number(volume.value);
  update();
  // A <source> can fail before this deferred script attaches its listener.
  if (audio.error || audio.networkState === HTMLMediaElement.NETWORK_NO_SOURCE) loadError();
  audio.hidden = true;
  cassette.hidden = false;
  player.querySelector('.cassette-settings').hidden = false;
}
