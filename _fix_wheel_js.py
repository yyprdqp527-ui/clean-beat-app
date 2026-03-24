#!/usr/bin/env python3
# coding: utf-8
"""Remplace les fonctions JS de la roue dans gameplay.html"""

with open('templates/gameplay.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx_spin = content.find('function spinWheel() {')
idx_close = content.find('\nfunction closeWheelResult()', idx_spin)
close_end = content.find('\n    }', idx_close)
close_end_final = content.find('\n}', close_end)
block_end = content.find('\n\n', close_end_final) + 2

old_block = content[idx_spin:block_end]
print(f"Remplacement du bloc {idx_spin}->{block_end} ({len(old_block)} chars)")

new_block = r"""function spinWheel() {
    if (isSpinning) return;
    isSpinning = true;
    const spinBtn = document.getElementById('spinBtn');
    spinBtn.disabled = true;
    spinBtn.textContent = '\u23f3 En cours...';
    const canvas = document.getElementById('wheelCanvas');
    const spins = 5 + Math.random() * 3;
    const extraDegrees = Math.random() * 360;
    const totalRotation = (spins * 360) + extraDegrees;
    canvas.style.transform = `rotate(${currentRotation + totalRotation}deg)`;
    const finalAngle = (currentRotation + totalRotation) % 360;
    const sliceAngle = 360 / wheelTasks.length;
    const selectedIndex = Math.floor((360 - finalAngle + sliceAngle / 2) / sliceAngle) % wheelTasks.length;
    const selectedTask = wheelTasks[selectedIndex];
    currentRotation = (currentRotation + totalRotation) % 360;
    setTimeout(() => {
        addWheelTaskCard(selectedTask);
        isSpinning = false;
        spinBtn.disabled = false;
        spinBtn.textContent = '\U0001f3af FAIRE TOURNER LA ROUE !';
    }, 4000);
}

function addWheelTaskCard(task) {
    const list = document.getElementById('wheelTaskList');
    if (!list) return;
    const emojiMatch = task.task.match(/^(\p{Emoji_Presentation}|\p{Emoji}\uFE0F|\p{Emoji_Modifier_Base})\s*/u);
    const emoji = emojiMatch ? emojiMatch[0].trim() : '\U0001f3af';
    const taskNameClean = emojiMatch ? task.task.slice(emojiMatch[0].length) : task.task;
    const card = document.createElement('div');
    card.className = 'wheel-task-card';
    const safeTask = task.task.replace(/'/g, '&#39;');
    card.innerHTML = `
        <div class="wtc-row1">
            <div class="wtc-emoji">${emoji}</div>
            <div class="wtc-info">
                <div class="wtc-name">${taskNameClean}</div>
                <div class="wtc-pts">+${task.points} pts si tu la fais !</div>
            </div>
        </div>
        <button class="wheel-validate-btn" onclick="validateWheelTask(this, '${safeTask}', ${task.points})">
            \u2705 J'ai fait la corv\xe9e !
        </button>
    `;
    list.insertBefore(card, list.firstChild);
    setTimeout(() => card.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 100);
}

function validateWheelTask(btn, taskName, points) {
    if (btn.classList.contains('done') || btn.disabled) return;
    btn.disabled = true;
    btn.textContent = '\u23f3 Validation\u2026';
    fetch('/api/complete_wheel_task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_name: taskName, points: points })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            btn.classList.add('done');
            btn.textContent = '\U0001f3c6 Corv\xe9e valid\xe9e !';
            floatPoints('+' + points + ' pts', btn);
            const counter = document.getElementById('myWheelPts');
            if (counter && data.new_total !== undefined) {
                counter.textContent = data.new_total;
                counter.style.animation = 'none';
                void counter.offsetHeight;
                counter.style.animation = 'bounce 0.5s ease';
            }
            const card = btn.closest('.wheel-task-card');
            if (card) {
                const pts = card.querySelector('.wtc-pts');
                if (pts) pts.textContent = '+' + points + ' pts gagn\xe9s \U0001f389';
            }
        } else {
            btn.disabled = false;
            btn.textContent = '\u2705 J\'ai fait la corv\xe9e !';
            alert(data.error || 'Erreur lors de la validation');
        }
    })
    .catch(() => {
        btn.disabled = false;
        btn.textContent = '\u2705 J\'ai fait la corv\xe9e !';
        alert('Erreur r\xe9seau, r\xe9essaie !');
    });
}

function floatPoints(text, anchorEl) {
    const rect = anchorEl.getBoundingClientRect();
    const el = document.createElement('div');
    el.className = 'points-animation';
    el.textContent = text;
    el.style.top = (rect.top + window.scrollY) + 'px';
    el.style.left = (rect.left + rect.width / 2) + 'px';
    el.style.transform = 'translateX(-50%)';
    el.style.color = '#FDAE54';
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2100);
}

function closeWheelResult() {
    document.getElementById('wheelResultOverlay').classList.remove('open');
}

"""

new_content = content[:idx_spin] + new_block + content[block_end:]

with open('templates/gameplay.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("OK: gameplay.html mis a jour")
print(f"Nouveau bloc: {len(new_block)} chars")
