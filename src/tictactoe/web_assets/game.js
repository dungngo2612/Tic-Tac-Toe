"use strict";

const byId = (id) => document.getElementById(id);
const board = byId("board");
const settings = byId("settings");
const entry = new URL(location.href);
const demoMode = entry.searchParams.get("demo") === "1";
const difficultyNames = {easy: "Dễ", medium: "Trung bình", hard: "Khó"};
const labels = {
  local: "Hai người cùng máy",
  minimax: "Minimax + Alpha-Beta",
  mcts: "MCTS + UCT",
  mcts_guarded: "MCTS có bảo vệ",
  random: "Bot ngẫu nhiên",
};
const agentHints = {
  local: "Hai người thay phiên đặt quân trên cùng một bàn.",
  mcts: "Ước lượng nước đi bằng các ván mô phỏng có seed.",
  mcts_guarded: "Bộ giải 3 × 3 lọc nước giữ được ít nhất hòa khi có thể.",
  random: "Chọn đều giữa các ô còn trống.",
};

let options = readDemoSettings();
let setupDraft;
let lastDifficulty = "medium";
let state = null;
let history = [];
let searches = new Map();
let scores = { 1: 0, 0: 0, "-1": 0 };
let counted = null;
let seed = 0;
let cells = [];
let focusIndex = 0;
let busy = "";
let controller = null;
let generation = 0;
let retry = null;
let hasMatch = false;

function readDemoSettings() {
  const draft = new FormData(settings);
  return {
    size: Number(draft.get("size")),
    agent: draft.get("agent"),
    human: Number(draft.get("human")),
    depth: Number(draft.get("depth")),
    iterations: Number(draft.get("iterations")),
    c: Number(draft.get("c")),
    rollout: draft.get("rollout"),
    policy: draft.get("policy"),
    tactical: draft.has("tactical"),
  };
}

function updateDemoSettings() {
  const size = Number(settings.elements.size.value);
  const agentSelect = settings.elements.agent;
  agentSelect.querySelector('[value="mcts_guarded"]').disabled = size !== 3;
  if (size !== 3 && agentSelect.value === "mcts_guarded") agentSelect.value = "minimax";
  const agent = agentSelect.value;
  byId("agent-hint").textContent = agent === "minimax"
    ? (size === 3 ? "Giải chính xác toàn bộ nước đi trên bàn 3 × 3."
      : "Tìm theo độ sâu và xét các ô gần quân đã đặt.")
    : agentHints[agent];
  byId("human-options").hidden = agent === "local";
  byId("depth-options").hidden = agent !== "minimax" || size === 3;
  byId("mcts-options").hidden = !agent.startsWith("mcts");
  byId("advanced").hidden = byId("depth-options").hidden && byId("mcts-options").hidden;
  byId("tactical-options").hidden = size === 3 || agent !== "mcts";
}

const symbol = (side) => side === 1 ? "X" : side === -1 ? "O" : "=";
const coordinate = (move) => String.fromCharCode(65 + move % options.size) + (Math.floor(move / options.size) + 1);
const isBot = (side) => options.agent !== "local" && side !== options.human;
const shouldPlayAI = () => state && state.outcome === null && isBot(state.turn);
const formatTime = (elapsed) => elapsed < 1 ? `${Math.round(elapsed * 1000)} ms` : `${elapsed.toFixed(2)} s`;
const undoIndex = () => history.findLastIndex((_, index) => !isBot(index % 2 === 0 ? 1 : -1));

function setError(message = "", operation = null) {
  byId("error").textContent = message;
  byId("error").hidden = !message;
  byId("retry").hidden = !operation;
  retry = operation;
}

function relocate(index, focus = false) {
  if (!cells.length) return;
  cells[focusIndex].tabIndex = -1;
  focusIndex = index;
  cells[focusIndex].tabIndex = 0;
  if (focus) cells[focusIndex].focus();
}

function makeBoard() {
  const size = options.size;
  const large = size === 15;
  cells = [];
  focusIndex = Math.floor(size * size / 2);
  board.classList.toggle("large", large);
  byId("zoom").hidden = !large;
  resetZoom();
  board.style.setProperty("--size", size);
  board.setAttribute("aria-label", `Bàn cờ ${size} nhân ${size}`);
  const fragment = document.createDocumentFragment();
  function axis(text) {
    const element = document.createElement("span");
    element.className = "axis";
    element.setAttribute("aria-hidden", "true");
    element.textContent = text;
    fragment.append(element);
  }
  axis("");
  for (let col = 0; col < size; col++) axis(String.fromCharCode(65 + col));
  for (let move = 0; move < size * size; move++) {
    if (move % size === 0) axis(String(Math.floor(move / size) + 1));
    const cell = document.createElement("button");
    cell.type = "button";
    cell.className = "cell";
    cell.classList.toggle("first-row", move < size);
    cell.classList.toggle("first-col", move % size === 0);
    cell.classList.toggle("center", move === Math.floor(size * size / 2));
    cell.dataset.index = String(move);
    cell.tabIndex = move === focusIndex ? 0 : -1;
    const piece = document.createElement("span");
    piece.setAttribute("aria-hidden", "true");
    cell.append(piece);
    cells.push(cell);
    fragment.append(cell);
  }
  board.replaceChildren(fragment);
}

function renderBoard() {
  const size = options.size;
  if (cells.length !== size * size) makeBoard();
  const line = new Set(state?.line ?? []);
  const canPlay = state && state.outcome === null && !busy && !isBot(state.turn);
  board.dataset.turn = symbol(state?.turn ?? 1).toLowerCase();
  cells.forEach((cell, index) => {
    const mark = state?.board[index] ?? 0;
    const side = mark ? symbol(mark).toLowerCase() : "";
    cell.dataset.side = side;
    cell.dataset.free = String(mark === 0);
    cell.classList.toggle("last", state?.last_move === index);
    cell.classList.toggle("won", line.has(index));
    cell.setAttribute("aria-disabled", String(!canPlay || mark !== 0));
    cell.setAttribute("aria-label", `${coordinate(index)}, ${mark ? symbol(mark) : "ô trống"}`);
    cell.firstElementChild.className = side ? `piece ${side}` : "";
  });
}

function renderStatus() {
  const opponent = options.difficulty
    ? `Máy · ${difficultyNames[options.difficulty]}` : labels[options.agent];
  let title = "Đang mở bàn cờ…";
  let detail = "";
  let mark = state?.turn ?? 1;
  if (retry) {
    title = "Lượt đi bị gián đoạn";
  } else if (state?.outcome === 0) {
    title = "Ván đấu hòa";
    detail = "Bàn cờ đã đầy";
    mark = 0;
  } else if (state && state.outcome !== null) {
    mark = state.outcome;
    title = options.agent === "local" ? `${symbol(mark)} thắng!`
      : mark === options.human ? "Bạn thắng!" : "AI thắng!";
    detail = `${symbol(mark)} nối ${state.line.length} quân`;
  } else if (state && isBot(mark)) {
    title = "AI đang nghĩ…";
    detail = opponent;
  } else if (state) {
    title = options.agent === "local" ? `Lượt của ${symbol(mark)}` : "Lượt của bạn";
    detail = `Chọn ô để đặt ${symbol(mark)}`;
  }
  byId("turn-mark").dataset.side = mark === 0 ? "draw" : symbol(mark).toLowerCase();
  byId("turn-mark").parentElement.classList.toggle("thinking", busy === "ai");
  for (const [id, value] of [["status-title", title], ["status-detail", detail]]) {
    if (byId(id).textContent !== value) byId(id).textContent = value;
  }
  byId("game-title").textContent = `${options.size} × ${options.size}`;
  byId("game-subtitle").textContent = `Nối ${options.size === 3 ? 3 : 5} quân liên tiếp`;
  byId("last-move").textContent = history.length
    ? `Vừa đi · ${symbol(history.length % 2 ? 1 : -1)} ${coordinate(history.at(-1))}` : "X đi trước";
  for (const [side, id] of [[1, "player-x"], [-1, "player-o"]]) {
    byId(id).textContent = options.agent === "local" ? `Người chơi ${symbol(side)}`
      : side === options.human ? "Bạn" : opponent;
  }
  byId("undo").disabled = busy === "state" || undoIndex() < 0;
  byId("score-x").textContent = scores[1];
  byId("score-o").textContent = scores[-1];
  byId("score-draw").textContent = scores[0];
  byId("resume").textContent = state && state.outcome !== null
    ? "Xem lại ván vừa chơi →" : "Tiếp tục ván đang chơi →";
}

function renderHistory() {
  byId("history-count").textContent = `${history.length} nước`;
  byId("history-empty").hidden = Boolean(history.length);
  const list = byId("history-list");
  list.replaceChildren(...history.map((move, index) => {
    const row = document.createElement("li");
    const side = index % 2 === 0 ? 1 : -1;
    const decision = searches.get(index);
    const gameNumber = document.createElement("small");
    const player = document.createElement("b");
    const position = document.createElement("span");
    const info = document.createElement("small");
    gameNumber.textContent = index + 1;
    player.textContent = symbol(side);
    player.className = side === 1 ? "x-color" : "o-color";
    position.textContent = coordinate(move);
    info.textContent = decision ? `AI · ${formatTime(decision.elapsed)}` : "";
    row.append(gameNumber, player, position, info);
    return row;
  }).reverse());
  const result = [...searches.values()].at(-1);
  byId("search").hidden = !demoMode || !result;
  if (!demoMode || !result) return;
  const selected = result.root.find((item) => item.move === result.move);
  const reasons = {win: "Thắng ngay", block: "Chặn thắng ngay", guarded: "Giữ thế ít nhất hòa", forced_loss: "Mọi nước đều thua nếu đối thủ đi tối ưu"};
  const entries = [["Nước đã chọn", coordinate(result.move)], ["Thời gian", formatTime(result.elapsed)]];
  if (result.nodes) entries.push(["Nút tìm kiếm", result.nodes]);
  if (options.agent === "minimax") entries.push(["Lần cắt nhánh", result.cutoffs]);
  if (result.iterations) {
    entries.push(["Rollout", result.rollouts], ["max_visits", coordinate(result.max_visits)], ["max_mean", coordinate(result.max_mean)]);
  }
  if (selected) entries.push(["Lượt thăm nước đã chọn", selected.visits], ["Điểm mô phỏng trung bình", selected.mean.toFixed(2)]);
  if (result.score !== null && options.size === 3) {
    entries.push(["Giá trị nước đã chọn", { "-1": "Thua", 0: "Hòa", 1: "Thắng" }[result.score]]);
  }
  if (result.reason) entries.push(["Lý do", reasons[result.reason]]);
  byId("search-details").replaceChildren(...entries.flatMap(([label, value]) => {
    const term = document.createElement("dt"), description = document.createElement("dd");
    term.textContent = label;
    description.textContent = value;
    return [term, description];
  }));
}

function render() {
  renderBoard();
  renderStatus();
  renderHistory();
}

function accept(response, moves, action) {
  state = response.state;
  history = moves.slice();
  searches = new Map([...searches].filter(([index]) => index < history.length));
  if (action === "ai") {
    searches.set(history.length, response.search);
    history.push(response.search.move);
  }
  if (counted !== state.outcome) {
    if (counted !== null) scores[counted]--;
    if (state.outcome !== null) scores[state.outcome]++;
    counted = state.outcome;
  }
}

async function request(action, moves = history) {
  const version = generation;
  controller = new AbortController();
  busy = action;
  setError();
  render();
  try {
    const {size, human, difficulty} = options;
    const config = difficulty ? {size, human, difficulty} : options;
    const result = await fetch("./api/game", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({...config, action, moves, seed}),
      signal: controller.signal,
    });
    const content = await result.json();
    if (!result.ok) throw new Error(content.error || "Máy chủ không xử lý được lượt đi.");
    if (version !== generation) return false;
    accept(content, moves, action);
    return true;
  } catch (error) {
    if (version !== generation) return false;
    const message = error instanceof TypeError ? "Không kết nối được với máy chủ trò chơi." : error.message;
    setError(message, () => continueGame(action, moves));
    return false;
  } finally {
    if (version === generation) {
      busy = "";
      controller = null;
      render();
    }
  }
}

async function continueGame(action, moves) {
  const version = generation;
  if (await request(action, moves) && version === generation && shouldPlayAI()) {
    await request("ai");
  }
}

function cancel() {
  generation++;
  controller?.abort();
  controller = null;
}

function newGame(next = options) {
  cancel();
  options = next;
  if (options.difficulty) lastDifficulty = options.difficulty;
  hasMatch = true;
  seed = crypto.getRandomValues(new Uint32Array(1))[0];
  history = [];
  state = null;
  searches.clear();
  counted = null;
  resetZoom();
  navigateTo("match");
  return continueGame("state", []);
}

board.addEventListener("click", (event) => {
  const cell = event.target.closest(".cell");
  if (!cell || cell.getAttribute("aria-disabled") === "true") return;
  const move = Number(cell.dataset.index);
  relocate(move);
  continueGame("state", [...history, move]);
});
board.addEventListener("focusin", (event) => {
  if (event.target.matches(".cell")) relocate(Number(event.target.dataset.index));
});
board.addEventListener("keydown", (event) => {
  if (!event.target.matches(".cell")) return;
  const index = Number(event.target.dataset.index), size = options.size;
  const row = Math.floor(index / size), col = index % size;
  const next = {
    ArrowUp: Math.max(0, row - 1) * size + col,
    ArrowDown: Math.min(size - 1, row + 1) * size + col,
    ArrowLeft: row * size + Math.max(0, col - 1),
    ArrowRight: row * size + Math.min(size - 1, col + 1),
    Home: row * size,
    End: row * size + size - 1,
  }[event.key];
  if (next !== undefined) {
    event.preventDefault();
    relocate(next, true);
  }
});
if (demoMode) settings.addEventListener("change", updateDemoSettings);
settings.addEventListener("submit", (event) => {
  event.preventDefault();
  let next = demoMode ? readDemoSettings() : setupDraft;
  if (next.difficulty) next = {...next, difficulty: settings.elements.difficulty.value};
  byId("setup").close();
  newGame(next);
});
byId("undo").addEventListener("click", () => {
  const index = undoIndex();
  if (index < 0) return;
  cancel();
  continueGame("state", history.slice(0, index));
});
function resetZoom() {
  byId("board-scroll").classList.remove("zoomed");
  byId("zoom").setAttribute("aria-pressed", "false");
  byId("zoom").textContent = "Phóng bàn";
}

byId("zoom").addEventListener("click", () => {
  const view = byId("board-scroll");
  const zoomed = view.classList.toggle("zoomed");
  byId("zoom").setAttribute("aria-pressed", String(zoomed));
  byId("zoom").textContent = zoomed ? "Thu nhỏ" : "Phóng bàn";
  if (zoomed) {
    const cell = cells[state?.last_move ?? focusIndex];
    const rect = cell.getBoundingClientRect();
    const viewport = view.getBoundingClientRect();
    view.scrollBy(rect.left - viewport.left + (rect.width - view.clientWidth) / 2,
      rect.top - viewport.top + (rect.height - view.clientHeight) / 2);
  }
});
function openSetup(draft) {
  setupDraft = draft;
  byId("demo-settings").hidden = !demoMode;
  byId("difficulty-options").hidden = !draft.difficulty;
  byId("settings-note").hidden = !history.length || state?.outcome !== null;
  byId("setup-title").textContent = demoMode ? "Thiết lập demo" : "Ván mới";
  for (const [name, value] of Object.entries(draft)) {
    const field = settings.elements.namedItem(name);
    if (field.type === "checkbox") field.checked = value;
    else field.value = String(value);
  }
  byId("advanced").open = false;
  if (demoMode) updateDemoSettings();
  byId("setup").showModal();
}
byId("reset").addEventListener("click", () => {
  if (!demoMode && options.agent === "local" && (!history.length || state?.outcome !== null)) {
    newGame();
  } else {
    openSetup(options);
  }
});
byId("retry").addEventListener("click", () => retry?.());
byId("open-help").addEventListener("click", () => byId("help").showModal());
byId("open-journal").addEventListener("click", () => byId("journal").showModal());

function showScreen(focus) {
  const playing = hasMatch && location.hash === "#choi";
  byId("lobby").hidden = playing;
  byId("game-layout").hidden = !playing;
  byId("resume").hidden = !hasMatch;
  document.title = playing ? "Caro Club · Bàn chơi" : "Caro Club · Sảnh chơi";
  if (focus) {
    byId(playing ? "match-title" : "lobby-title").focus({preventScroll: true});
    window.scrollTo(0, 0);
  }
}

function navigateTo(screen) {
  const hash = screen === "match" ? "#choi" : "";
  if (location.hash !== hash) window.history.pushState(null, "", location.pathname + location.search + hash);
  showScreen(true);
}

const lobbySizes = document.querySelectorAll('input[name="lobby-size"]');
function setLobbySize(size) {
  for (const input of lobbySizes) input.checked = Number(input.value) === size;
  byId("lobby-rule").textContent = `X đi trước. Nối ${size === 3 ? 3 : 5} quân liên tiếp theo hàng ngang, dọc hoặc chéo để thắng.`;
}
for (const input of lobbySizes) {
  input.addEventListener("change", () => setLobbySize(Number(input.value)));
}

function startFromLobby(mode, size) {
  if (location.protocol === "file:") {
    const server = new URL("http://127.0.0.1:8765/");
    server.search = new URLSearchParams({mode, size});
    if (demoMode) server.searchParams.set("demo", "1");
    location.assign(server);
    return;
  }
  const replacingMatch = history.length && state?.outcome === null;
  if (!demoMode) {
    if (mode === "solo") {
      openSetup({size, human: 1, difficulty: lastDifficulty});
    } else {
      const draft = {size, human: 1, agent: "local"};
      if (replacingMatch) openSetup(draft);
      else newGame(draft);
    }
    return;
  }
  let agent = mode === "duo" ? "local" : options.agent;
  if (mode === "solo" && (agent === "local" || (agent === "mcts_guarded" && size !== 3))) agent = "minimax";
  const draft = {...options, size, agent};
  if (mode === "solo" || replacingMatch) openSetup(draft);
  else newGame(draft);
}
for (const mode of ["solo", "duo"]) {
  byId(mode).addEventListener("click", () => {
    const size = Number(document.querySelector('input[name="lobby-size"]:checked').value);
    startFromLobby(mode, size);
  });
}
byId("back-lobby").addEventListener("click", () => {
  setLobbySize(options.size);
  navigateTo("lobby");
});
byId("resume").addEventListener("click", () => navigateTo("match"));
window.addEventListener("popstate", () => showScreen(true));

byId("launcher").hidden = location.protocol !== "file:";
const mode = entry.searchParams.get("mode");
if (location.protocol !== "file:" && ["solo", "duo"].includes(mode)) {
  const size = entry.searchParams.get("size") === "3" ? 3 : 15;
  entry.searchParams.delete("mode");
  entry.searchParams.delete("size");
  window.history.replaceState(null, "", entry.pathname + entry.search);
  setLobbySize(size);
  startFromLobby(mode, size);
} else {
  if (location.hash === "#choi") window.history.replaceState(null, "", location.pathname + location.search);
  showScreen(false);
}
