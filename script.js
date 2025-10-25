// Tab Navigation
function showTab(section) {
  document.querySelectorAll('.section').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById(section).classList.add('active');
  document.getElementById(`tab-${section}`).classList.add('active');
}

// Login Form Submission
document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const name = document.getElementById('name').value.trim();
  const roll = document.getElementById('roll').value.trim();

  if (!name || !roll) {
    alert('Please enter both Name and Roll Number.');
    return;
  }

  const formData = new FormData();
  formData.append('name', name);
  formData.append('roll', roll);

  try {
    const res = await fetch('/login', {
      method: 'POST',
      body: formData  // Browser sets correct Content-Type
    });

    const data = await res.json();

    if (res.ok && data.success) {
      document.getElementById('greeting-name').textContent = name;
      document.getElementById('greeting-roll').textContent = roll;
      showTab('upload');
    } else {
      alert(data.error || 'Login failed. Please try again.');
    }
  } catch (err) {
    console.error(err);
    alert('Network error. Is the server running?');
  }
});

// Upload & Grade
document.getElementById('uploadForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById('pdf-file');
  const file = fileInput.files[0];
  const week = document.getElementById('week-select').value;

  if (!file) {
    alert('Please select a PDF file.');
    return;
  }

  const formData = new FormData();
  formData.append('pdf', file);
  formData.append('week', week);

  const resultDiv = document.getElementById('result');
  resultDiv.innerHTML = '<p>Grading your answers... 📝</p>';
  resultDiv.classList.remove('hidden');

  try {
    const res = await fetch('/grade', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();

    if (res.ok && data.success) {
      let msg = `<h3>✅ Your Score: ${data.percentage}% (${data.score}/${data.total})</h3>`;
      if (data.is_top) {
        msg += '<p style="color: gold; font-weight: bold; font-size: 1.2em;">🌟 Top Performer! 🌟</p>';
        // Optional: add confetti here later
      }
      resultDiv.innerHTML = msg;
    } else {
      resultDiv.innerHTML = `<p style="color: #ff6b6b;">❌ ${data.error || 'Grading failed'}</p>`;
    }
  } catch (err) {
    console.error(err);
    resultDiv.innerHTML = '<p style="color: #ff6b6b;">❌ Network error during grading.</p>';
  }
});

// Leaderboard Loading
async function loadLeaderboard() {
  const week = document.getElementById('lb-week').value;
  const list = document.getElementById('leaderboard-list');
  list.innerHTML = '<p>Loading...</p>';

  try {
    const res = await fetch(`/api/leaderboard?week=${encodeURIComponent(week)}`);
    const data = await res.json();

    if (!Array.isArray(data) || data.length === 0) {
      list.innerHTML = '<p>No scores yet for this week.</p>';
      return;
    }

    list.innerHTML = data.map((student, i) => {
      const rank = i + 1;
      let medal = rank;
      let rankClass = '';
      if (rank === 1) {
        medal = '🥇';
        rankClass = ' rank-1';
      } else if (rank === 2) {
        medal = '🥈';
        rankClass = ' rank-2';
      } else if (rank === 3) {
        medal = '🥉';
        rankClass = ' rank-3';
      }

      return `
        <div class="leaderboard-item${rankClass}">
          <span><strong>${medal}</strong> ${student.name} (${student.roll})</span>
          <span>${student.score}%</span>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error(err);
    list.innerHTML = '<p style="color: #ff6b6b;">Failed to load leaderboard.</p>';
  }
}

// Trigger leaderboard load on tab click and initial load
document.getElementById('tab-leaderboard').addEventListener('click', loadLeaderboard);
loadLeaderboard(); // Load default (Week 1) on page load