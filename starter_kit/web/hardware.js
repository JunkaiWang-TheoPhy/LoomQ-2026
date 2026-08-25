(() => {
  const cards = document.querySelector('#hardware-backends');
  const select = document.querySelector('#hardware-backend-select');
  const submit = document.querySelector('#hardware-submit');
  const qasm = document.querySelector('#hardware-qasm');
  const shots = document.querySelector('#hardware-shots');
  const status = document.querySelector('#hardware-job-status');
  const result = document.querySelector('#hardware-result');
  if (!cards || !select || !submit) return;

  let backends = [];
  const api = async (path, options = {}) => {
    const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload?.error?.message || '请求失败');
    return payload;
  };

  const statusLabel = {
    ready: '可提交',
    fixture_available: 'QA fixture（非真机）',
    configuration_required: '需要配置凭证',
    adapter_required: '需要安装 provider adapter',
  };

  const updateSubmitState = () => {
    const backend = backends.find((item) => item.id === select.value);
    submit.disabled = !backend || !['ready', 'fixture_available'].includes(backend.status);
  };

  const render = (payload) => {
    backends = payload.backends;
    cards.replaceChildren(...backends.map((backend) => {
      const item = document.createElement('span');
      item.className = `hardware-backend-status ${backend.status}`;
      item.textContent = `${backend.name} · ${statusLabel[backend.status] || backend.status}`;
      return item;
    }));
    select.replaceChildren(...backends.map((backend) => {
      const option = document.createElement('option');
      option.value = backend.id;
      option.textContent = `${backend.name} · ${statusLabel[backend.status] || backend.status}`;
      option.disabled = !['ready', 'fixture_available'].includes(backend.status);
      return option;
    }));
    const firstQpu = backends.find((backend) => backend.kind === 'qpu');
    if (firstQpu) select.value = firstQpu.id;
    updateSubmitState();
  };

  select.addEventListener('change', updateSubmitState);
  api('/api/hardware/backends').then(render).catch((error) => {
    cards.textContent = `后端状态读取失败：${error.message}`;
  });

  submit.addEventListener('click', async () => {
    submit.disabled = true;
    result.hidden = true;
    status.textContent = '正在提交，保留 job ID 后轮询…';
    try {
      const job = await api('/api/hardware/submit', {
        method: 'POST',
        body: JSON.stringify({ backend: select.value, qasm: qasm.value, shots: Number(shots.value) }),
      });
      const completed = await api(`/api/hardware/jobs/${encodeURIComponent(job.job_id)}`);
      status.textContent = `${completed.provenance.kind === 'hardware' ? '真机任务完成' : 'QA fixture 完成'} · job ${completed.job_id}`;
      result.textContent = JSON.stringify({
        backend: completed.backend,
        job_id: completed.job_id,
        shots: completed.shots,
        counts: completed.counts,
        bit_order: completed.bit_order,
        timestamp: completed.timestamp,
        provenance: completed.provenance,
      }, null, 2);
      result.hidden = false;
    } catch (error) {
      status.textContent = `提交失败：${error.message}`;
    } finally {
      updateSubmitState();
    }
  });
})();
