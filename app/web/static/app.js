async function postAction(path) {
  await fetch(path, { method: 'POST' });
}

async function refreshState() {
  const target = document.getElementById('result-json');
  if (!target) return;
  const rsp = await fetch('/api/state');
  const payload = await rsp.json();
  document.getElementById('system-state').innerText = payload.system_state;
  document.getElementById('recipe-name').innerText = payload.recipe || 'none';
  target.innerText = JSON.stringify(payload.last_result, null, 2);
}
setInterval(refreshState, 1000);

const teachCanvas = document.getElementById('roi-canvas');
const teachStream = document.getElementById('teach-stream');
const slotDefs = [];
let startPt = null;

if (teachCanvas && teachStream) {
  teachStream.onload = () => {
    teachCanvas.width = teachStream.clientWidth;
    teachCanvas.height = teachStream.clientHeight;
  };
  const ctx = teachCanvas.getContext('2d');

  teachCanvas.addEventListener('mousedown', (e) => {
    const rect = teachCanvas.getBoundingClientRect();
    startPt = [e.clientX - rect.left, e.clientY - rect.top];
  });

  teachCanvas.addEventListener('mouseup', (e) => {
    if (!startPt) return;
    const rect = teachCanvas.getBoundingClientRect();
    const endPt = [e.clientX - rect.left, e.clientY - rect.top];
    const x = Math.min(startPt[0], endPt[0]);
    const y = Math.min(startPt[1], endPt[1]);
    const w = Math.abs(startPt[0] - endPt[0]);
    const h = Math.abs(startPt[1] - endPt[1]);
    const idx = slotDefs.length + 1;
    slotDefs.push({
      slot_id: `slot_${idx}`,
      label: `Slot ${idx}`,
      roi: [Math.round(x), Math.round(y), Math.round(w), Math.round(h)],
      expected_center: [Math.round(x + w / 2), Math.round(y + h / 2)],
      position_tolerance_px: 10,
      presence_threshold: 0.55,
      orientation_threshold: 0.2,
      orientation_mode: 'moments',
      inspection_mode: 'presence_position_orientation',
      required: true,
      template_path: null
    });
    ctx.strokeStyle = '#00ff00';
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);
    ctx.fillStyle = '#00ff00';
    ctx.fillText(`Slot ${idx}`, x + 2, y + 12);
    startPt = null;
  });
}

async function saveTeachRecipe() {
  const form = document.getElementById('teach-form');
  const body = {
    name: form.name.value,
    description: form.description.value,
    stable_frames_required: 4,
    slots: slotDefs
  };
  const rsp = await fetch('/teach', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const payload = await rsp.json();
  alert(`Saved recipe ${payload.recipe}`);
}
