/**
 * Scion Task Board Demo - Frontend Client Logic
 * Uses relative API endpoints ('api/tasks', etc.) to work seamlessly
 * behind the Scion Hub reverse proxy or directly via localhost.
 */

// Determine API base path dynamically so it respects reverse proxy subpaths
const getApiUrl = (endpoint) => {
  // Ensure relative path without leading slash so it preserves current base URL
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  return cleanEndpoint;
};

let tasks = [];
let editingTaskId = null;

// DOM Elements
const listTodo = document.getElementById('listTodo');
const listProgress = document.getElementById('listProgress');
const listDone = document.getElementById('listDone');

const countTodo = document.getElementById('countTodo');
const countProgress = document.getElementById('countProgress');
const countDone = document.getElementById('countDone');

const statTotal = document.getElementById('statTotal');
const statTodo = document.getElementById('statTodo');
const statProgress = document.getElementById('statProgress');
const statDone = document.getElementById('statDone');

const searchInput = document.getElementById('searchInput');
const priorityFilter = document.getElementById('priorityFilter');

const taskModal = document.getElementById('taskModal');
const taskForm = document.getElementById('taskForm');
const modalTitle = document.getElementById('modalTitle');
const taskIdInput = document.getElementById('taskId');
const taskTitleInput = document.getElementById('taskTitle');
const taskDescriptionInput = document.getElementById('taskDescription');
const taskStatusInput = document.getElementById('taskStatus');
const taskPriorityInput = document.getElementById('taskPriority');

const openAddModalBtn = document.getElementById('openAddModalBtn');
const closeModalBtn = document.getElementById('closeModalBtn');
const cancelModalBtn = document.getElementById('cancelModalBtn');
const resetBtn = document.getElementById('resetBtn');
const toastContainer = document.getElementById('toastContainer');
const connectionStatus = document.getElementById('connectionStatus');

// Toast Notification
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = 'toast';
  const icon = type === 'success' ? '✓' : type === 'error' ? '⚠' : 'ℹ';
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Fetch all tasks from API
async function loadTasks() {
  try {
    const res = await fetch(getApiUrl('api/tasks'));
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    const data = await res.json();
    tasks = data.tasks || [];
    renderTasks();
    updateStats();
    updateConnectionStatus(true);
  } catch (err) {
    console.error('Failed to load tasks:', err);
    updateConnectionStatus(false);
  }
}

function updateConnectionStatus(isOnline) {
  const dot = connectionStatus.querySelector('.status-dot');
  const text = connectionStatus.querySelector('.status-text');
  if (isOnline) {
    dot.style.background = '#22c55e';
    dot.style.boxShadow = '0 0 8px #22c55e';
    text.textContent = 'Hub Proxy Active';
  } else {
    dot.style.background = '#ef4444';
    dot.style.boxShadow = '0 0 8px #ef4444';
    text.textContent = 'Connecting...';
  }
}

// Filter tasks based on search & priority
function getFilteredTasks() {
  const query = searchInput.value.trim().toLowerCase();
  const priority = priorityFilter.value;

  return tasks.filter(task => {
    const matchesQuery = !query ||
      task.title.toLowerCase().includes(query) ||
      (task.description && task.description.toLowerCase().includes(query));

    const matchesPriority = priority === 'all' || task.priority === priority;
    return matchesQuery && matchesPriority;
  });
}

// Render cards into columns
function renderTasks() {
  const filtered = getFilteredTasks();

  const todoTasks = filtered.filter(t => t.status === 'todo');
  const progressTasks = filtered.filter(t => t.status === 'in_progress');
  const doneTasks = filtered.filter(t => t.status === 'done');

  listTodo.innerHTML = todoTasks.map(t => createTaskCard(t)).join('');
  listProgress.innerHTML = progressTasks.map(t => createTaskCard(t)).join('');
  listDone.innerHTML = doneTasks.map(t => createTaskCard(t)).join('');

  countTodo.textContent = todoTasks.length;
  countProgress.textContent = progressTasks.length;
  countDone.textContent = doneTasks.length;
}

// Create single card HTML
function createTaskCard(task) {
  const priorityClass = `priority-${task.priority || 'medium'}`;
  const priorityLabel = (task.priority || 'medium').toUpperCase();
  const createdDate = new Date(task.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  // Move buttons
  let moveButtons = '';
  if (task.status === 'todo') {
    moveButtons = `<button class="card-btn" onclick="moveTaskStatus(${task.id}, 'in_progress')" title="Start task">Start →</button>`;
  } else if (task.status === 'in_progress') {
    moveButtons = `
      <button class="card-btn" onclick="moveTaskStatus(${task.id}, 'todo')" title="Move back to Todo">← Todo</button>
      <button class="card-btn" onclick="moveTaskStatus(${task.id}, 'done')" title="Mark as Done">Done →</button>
    `;
  } else if (task.status === 'done') {
    moveButtons = `<button class="card-btn" onclick="moveTaskStatus(${task.id}, 'in_progress')" title="Reopen task">← Reopen</button>`;
  }

  return `
    <div class="task-card" id="task-${task.id}">
      <div class="task-card-header">
        <h4 class="task-title">${escapeHtml(task.title)}</h4>
        <span class="priority-tag ${priorityClass}">${priorityLabel}</span>
      </div>
      ${task.description ? `<p class="task-description">${escapeHtml(task.description)}</p>` : ''}
      <div class="task-footer">
        <span class="task-time">${createdDate}</span>
        <div class="task-actions">
          ${moveButtons}
          <button class="card-btn" onclick="openEditModal(${task.id})" title="Edit Task">✎</button>
          <button class="card-btn card-btn-delete" onclick="deleteTask(${task.id})" title="Delete Task">🗑</button>
        </div>
      </div>
    </div>
  `;
}

// Update dashboard statistics
function updateStats() {
  const total = tasks.length;
  const todo = tasks.filter(t => t.status === 'todo').length;
  const progress = tasks.filter(t => t.status === 'in_progress').length;
  const done = tasks.filter(t => t.status === 'done').length;

  statTotal.textContent = total;
  statTodo.textContent = todo;
  statProgress.textContent = progress;
  statDone.textContent = done;
}

// Move task status directly
window.moveTaskStatus = async function(id, newStatus) {
  try {
    const res = await fetch(getApiUrl(`api/tasks/${id}`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
    if (!res.ok) throw new Error('Failed to update task');
    const updated = await res.json();
    tasks = tasks.map(t => t.id === id ? updated : t);
    renderTasks();
    updateStats();
    showToast(`Task moved to ${newStatus.replace('_', ' ')}`, 'success');
  } catch (err) {
    console.error('Error updating status:', err);
    showToast('Failed to update task status', 'error');
  }
};

// Delete task
window.deleteTask = async function(id) {
  if (!confirm('Are you sure you want to delete this task?')) return;
  try {
    const res = await fetch(getApiUrl(`api/tasks/${id}`), {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error('Failed to delete task');
    tasks = tasks.filter(t => t.id !== id);
    renderTasks();
    updateStats();
    showToast('Task deleted successfully', 'success');
  } catch (err) {
    console.error('Error deleting task:', err);
    showToast('Failed to delete task', 'error');
  }
};

// Modal Operations
function openCreateModal() {
  editingTaskId = null;
  modalTitle.textContent = 'Create New Task';
  taskForm.reset();
  taskIdInput.value = '';
  taskStatusInput.value = 'todo';
  taskPriorityInput.value = 'medium';
  taskModal.style.display = 'flex';
  taskTitleInput.focus();
}

window.openEditModal = function(id) {
  const task = tasks.find(t => t.id === id);
  if (!task) return;

  editingTaskId = id;
  modalTitle.textContent = 'Edit Task';
  taskIdInput.value = task.id;
  taskTitleInput.value = task.title;
  taskDescriptionInput.value = task.description || '';
  taskStatusInput.value = task.status;
  taskPriorityInput.value = task.priority || 'medium';
  taskModal.style.display = 'flex';
  taskTitleInput.focus();
};

function closeModal() {
  taskModal.style.display = 'none';
  taskForm.reset();
  editingTaskId = null;
}

// Form Submission (Create or Edit)
taskForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const title = taskTitleInput.value.trim();
  const description = taskDescriptionInput.value.trim();
  const status = taskStatusInput.value;
  const priority = taskPriorityInput.value;

  if (!title) return;

  try {
    if (editingTaskId) {
      // Edit task
      const res = await fetch(getApiUrl(`api/tasks/${editingTaskId}`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description, status, priority })
      });
      if (!res.ok) throw new Error('Failed to update task');
      const updated = await res.json();
      tasks = tasks.map(t => t.id === editingTaskId ? updated : t);
      showToast('Task updated successfully', 'success');
    } else {
      // Create task
      const res = await fetch(getApiUrl('api/tasks'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, description, status, priority })
      });
      if (!res.ok) throw new Error('Failed to create task');
      const created = await res.json();
      tasks.push(created);
      showToast('Task created successfully', 'success');
    }

    renderTasks();
    updateStats();
    closeModal();
  } catch (err) {
    console.error('Error saving task:', err);
    showToast('Failed to save task', 'error');
  }
});

// Reset demo data
resetBtn.addEventListener('click', async () => {
  if (!confirm('Reset all demo tasks back to initial state?')) return;
  try {
    const res = await fetch(getApiUrl('api/reset'), { method: 'POST' });
    if (!res.ok) throw new Error('Reset failed');
    await loadTasks();
    showToast('Demo data reset to default', 'success');
  } catch (err) {
    console.error('Error resetting:', err);
    showToast('Failed to reset data', 'error');
  }
});

// Event Listeners for search & filters
searchInput.addEventListener('input', renderTasks);
priorityFilter.addEventListener('change', renderTasks);

openAddModalBtn.addEventListener('click', openCreateModal);
closeModalBtn.addEventListener('click', closeModal);
cancelModalBtn.addEventListener('click', closeModal);
taskModal.addEventListener('click', (e) => {
  if (e.target === taskModal) closeModal();
});

// Helper: Escape HTML strings
function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Initial load & Polling for live updates
loadTasks();
setInterval(loadTasks, 4000);
