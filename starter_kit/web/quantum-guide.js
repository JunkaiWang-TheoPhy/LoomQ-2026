(() => {
  const lessonList = document.querySelector('#quantum-guide-lessons');
  const face = document.querySelector('#quantum-guide-face');
  const faceState = document.querySelector('#quantum-guide-face-state');
  const copy = document.querySelector('#quantum-guide-copy');
  const status = document.querySelector('#quantum-guide-status');
  const measureButton = document.querySelector('#quantum-guide-measure');
  const concept = document.querySelector('#quantum-guide-concept-copy');
  const qasm = document.querySelector('#quantum-guide-qasm');
  if (!lessonList || !face || !measureButton) return;

  const api = async (path, options = {}) => {
    const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload?.error?.message || '请求失败');
    return payload;
  };

  const renderIntro = (intro) => {
    lessonList.replaceChildren(...intro.lessons.map((lesson, index) => {
      const item = document.createElement('li');
      item.dataset.lessonId = lesson.id;
      item.innerHTML = `<span>${index + 1}</span><strong>${lesson.title}</strong><small>${lesson.action}</small>`;
      item.addEventListener('click', () => {
        concept.innerHTML = `<h3>${lesson.title}</h3><p>${lesson.concept}</p>`;
        if (lesson.boundary) {
          const boundary = document.createElement('small');
          boundary.className = 'quantum-guide-boundary';
          boundary.textContent = `边界：${lesson.boundary}`;
          concept.append(boundary);
        }
      });
      return item;
    }));
    qasm.textContent = intro.mechanic.qasm.split('\n').filter((line) => line.includes('h ') || line.includes('measure')).join('  ·  ');
  };

  const renderMeasurement = (result) => {
    face.src = result.asset;
    face.alt = `${result.face_label}：${result.copy}`;
    faceState.textContent = `${result.outcome} · ${result.face_label}`;
    copy.textContent = result.copy;
    const simulatorLabel = result.source === 'local-exact-simulator' ? '本地精确模拟器（local-exact-simulator）' : result.source;
    status.textContent = `已由 ${simulatorLabel} 完成测量；概率为 0=${result.probabilities['0']}，1=${result.probabilities['1']}。`;
    measureButton.textContent = '再测一次';
    document.querySelector('[data-lesson-id="bit-and-measurement"]')?.classList.add('complete');
    document.querySelector('[data-lesson-id="superposition"]')?.classList.add('complete');
  };

  api('/api/quantum-intro').then(renderIntro).catch((error) => {
    status.textContent = `入门手册暂时无法加载：${error.message}`;
  });

  measureButton.addEventListener('click', async () => {
    measureButton.disabled = true;
    status.textContent = '正在运行本地精确模拟器…';
    try {
      renderMeasurement(await api('/api/quantum-intro/measure', { method: 'POST', body: '{}' }));
    } catch (error) {
      status.textContent = `测量失败：${error.message}`;
    } finally {
      measureButton.disabled = false;
    }
  });
})();
