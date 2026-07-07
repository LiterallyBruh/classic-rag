// Сборка презентации для защиты (Junior ML Contest, питч 5 минут):
// node scripts/build_presentation.js  ->  docs/presentation.pptx
// Все цифры — из eval/report.md и eval/baseline_comparison.md.
// Палитра: берри/крем (классическая литература), шрифты Arial/Cambria.

const path = require("path");
const NODE_GLOBAL = "/opt/homebrew/lib/node_modules";
const req = (m) => require(require.resolve(m, { paths: [NODE_GLOBAL] }));

const pptxgen = req("pptxgenjs");
const React = req("react");
const ReactDOMServer = req("react-dom/server");
const sharp = req("sharp");
const {
  FaBookOpen, FaQuoteRight, FaSearch, FaCogs, FaRobot, FaChartBar,
  FaUserGraduate, FaChalkboardTeacher, FaUniversity, FaCheckCircle,
  FaTimesCircle, FaGithub, FaComments, FaDatabase, FaExclamationTriangle,
} = req("react-icons/fa");

const BERRY = "6D2E46", ROSE = "A26769", CREAM = "ECE2D0",
      INK = "2B2B2B", MUT = "6E6E6E", OK = "2C5F2D", BAD = "990011",
      TINT = "F7F2EC", WHITE = "FFFFFF";

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(Comp, { color: `#${color}`, size: String(size) }));
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}
const shadow = () => ({ type: "outer", color: "000000", blur: 7, offset: 2, angle: 45, opacity: 0.13 });

(async () => {
  const icons = {};
  for (const [k, [c, col]] of Object.entries({
    book: [FaBookOpen, CREAM], quote: [FaQuoteRight, BERRY], search: [FaSearch, BERRY],
    cogs: [FaCogs, BERRY], robot: [FaRobot, BERRY], chart: [FaChartBar, BERRY],
    pupil: [FaUserGraduate, BERRY], teacher: [FaChalkboardTeacher, BERRY],
    student: [FaUniversity, BERRY], ok: [FaCheckCircle, OK], no: [FaTimesCircle, BAD],
    gh: [FaGithub, CREAM], fb: [FaComments, BERRY], db: [FaDatabase, BERRY],
    warn: [FaExclamationTriangle, BAD], bookB: [FaBookOpen, BERRY],
  })) icons[k] = await icon(c, col);

  const p = new pptxgen();
  p.layout = "LAYOUT_16x9";
  p.title = "ClassicLiteratureRAG — Junior ML Contest";

  const title = (s, t) => s.addText(t, {
    x: 0.5, y: 0.28, w: 9, h: 0.6, fontFace: "Cambria", fontSize: 27,
    bold: true, color: INK, margin: 0,
  });

  // ── 1. Титул ────────────────────────────────────────────────────────────
  let s = p.addSlide();
  s.background = { color: BERRY };
  s.addImage({ data: icons.book, x: 4.55, y: 0.75, w: 0.9, h: 0.9 });
  s.addText("ClassicLiteratureRAG", {
    x: 0.5, y: 1.85, w: 9, h: 0.85, align: "center", fontFace: "Cambria",
    fontSize: 44, bold: true, color: WHITE,
  });
  s.addText([
    { text: "Ответы по тексту классики — с цитатой и адресом главы.", options: { breakLine: true } },
    { text: "Без выдумок.", options: { bold: true } },
  ], { x: 1.2, y: 2.75, w: 7.6, h: 0.8, align: "center", fontSize: 17, color: CREAM, italic: true });
  s.addText([
    { text: "Демо: huggingface.co/spaces/ArtemResearch/ClassicLiteratureRAG", options: { breakLine: true } },
    { text: "Код: github.com/LiterallyBruh/classic-rag" },
  ], { x: 1.2, y: 4.35, w: 7.6, h: 0.7, align: "center", fontSize: 13, color: "D9C7CE" });
  s.addText("Junior ML Contest · AI Talent Hub, ИТМО · 2026", {
    x: 1.2, y: 5.05, w: 7.6, h: 0.35, align: "center", fontSize: 12, color: ROSE });
  s.addNotes("Здравствуйте! Покажу ClassicLiteratureRAG — вопросно-ответную систему по классической литературе, которая отвечает только по тексту первоисточника. 10 секунд: название, одна фраза сути — и сразу к проблеме.");

  // ── 2. Проблема ─────────────────────────────────────────────────────────
  s = p.addSlide(); s.background = { color: WHITE };
  title(s, "Проблема: LLM уверенно выдумывают классику");
  const stat = (x, big, cap) => {
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 1.05, w: 2.75, h: 1.9, rectRadius: 0.09, fill: { color: TINT }, shadow: shadow() });
    s.addText(big, { x, y: 1.2, w: 2.75, h: 1.0, align: "center", fontSize: 54, bold: true, color: BAD, fontFace: "Cambria" });
    s.addText(cap, { x: x + 0.15, y: 2.2, w: 2.45, h: 0.68, align: "center", fontSize: 12.5, color: INK });
  };
  stat(0.5, "0 / 27", "«цитат» GigaChat нашлись в тексте дословно");
  stat(3.62, "2 / 15", "верных номеров главы в его ответах");
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 6.75, y: 1.05, w: 2.75, h: 1.9, rectRadius: 0.09, fill: { color: TINT }, shadow: shadow() });
  s.addImage({ data: icons.warn, x: 7.85, y: 1.35, w: 0.55, h: 0.55 });
  s.addText("ответ нечем проверить, а цена ошибки — оценка на экзамене", { x: 6.95, y: 2.05, w: 2.35, h: 0.8, align: "center", fontSize: 12.5, color: INK, valign: "top" });
  s.addText("Кому это важно:", { x: 0.5, y: 3.3, w: 4, h: 0.4, fontSize: 14, bold: true, color: INK, margin: 0 });
  const aud = (x, ic, t) => {
    s.addImage({ data: icons[ic], x, y: 3.85, w: 0.42, h: 0.42 });
    s.addText(t, { x: x + 0.55, y: 3.78, w: 2.6, h: 0.6, fontSize: 13, color: INK, valign: "middle", margin: 0 });
  };
  aud(0.5, "pupil", "школьники — сочинения, ЕГЭ");
  aud(3.62, "student", "студенты-гуманитарии");
  aud(6.75, "teacher", "преподаватели литературы");
  s.addText("Замер на 29 вопросах нашего eval-набора — методика на слайде 7", { x: 0.5, y: 4.85, w: 9, h: 0.35, fontSize: 11, italic: true, color: MUT, margin: 0 });
  s.addNotes("Мы не просто заявляем проблему — мы её измерили: тот же GigaChat без RAG на наших 29 вопросах: ни одна из 27 закавыченных цитат не нашлась в тексте дословно, глава верна 2 раза из 15. Для школьника перед ЕГЭ такой ответ опасен.");

  // ── 3. Решение ──────────────────────────────────────────────────────────
  s = p.addSlide(); s.background = { color: WHITE };
  title(s, "Решение: ответ только по первоисточнику");
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 1.0, w: 5.6, h: 2.5, rectRadius: 0.09, fill: { color: TINT }, shadow: shadow() });
  s.addImage({ data: icons.quote, x: 0.75, y: 1.25, w: 0.4, h: 0.4 });
  s.addText([
    { text: "— Кому принадлежит «мир спасёт красота»?", options: { italic: true, color: MUT, breakLine: true, paraSpaceAfter: 8 } },
    { text: "Слова передают со слов князя Мышкина: «правда, князь, что вы раз говорили, что мир спасёт „красота“?»", options: { breakLine: true, paraSpaceAfter: 6 } },
    { text: "(Идиот, часть 3, глава 5)", options: { bold: true, color: BERRY } },
  ], { x: 1.3, y: 1.2, w: 4.6, h: 2.2, fontSize: 13 });
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 6.35, y: 1.0, w: 3.15, h: 2.5, rectRadius: 0.09, fill: { color: "F3E9E9" }, shadow: shadow() });
  s.addText("Если ответа в тексте нет:", { x: 6.55, y: 1.25, w: 2.8, h: 0.4, fontSize: 12.5, bold: true, color: INK, margin: 0 });
  s.addText("«В предоставленных фрагментах текста ответа нет»", { x: 6.55, y: 1.75, w: 2.8, h: 0.85, fontSize: 13, italic: true, color: BAD, margin: 0 });
  s.addText("честный отказ вместо правдоподобного вымысла", { x: 6.55, y: 2.75, w: 2.8, h: 0.6, fontSize: 11.5, color: MUT, margin: 0 });
  s.addText("Почему не хватает существующего:", { x: 0.5, y: 3.75, w: 5, h: 0.35, fontSize: 14, bold: true, color: INK, margin: 0 });
  s.addTable([
    ["LLM-чаты", "ответ непроверяем — см. слайд 2"],
    ["Краткие содержания (Брифли)", "нет цитат и адресов для сочинения"],
    ["Поиск по тексту (Ctrl+F)", "не понимает перефразировок и «Родю»"],
  ], { x: 0.5, y: 4.15, w: 9.0, colW: [3.1, 5.9], fontSize: 12, color: INK,
       border: { pt: 0.5, color: "D8CFC4" }, fill: { color: WHITE },
       margin: [0.04, 0.08, 0.04, 0.08] });
  s.addNotes("Каждое утверждение — с дословной цитатой и адресом часть/глава: это можно проверить за минуту. А если в тексте ответа нет, система отказывается. Альтернативы этого не дают: чаты непроверяемы, краткие содержания без цитат, Ctrl+F не знает, что Родя — это Раскольников.");

  // ── 4. Данные ───────────────────────────────────────────────────────────
  s = p.addSlide(); s.background = { color: WHITE };
  title(s, "Данные: воспроизводимый корпус и проверенный eval");
  s.addImage({ data: icons.bookB, x: 0.5, y: 1.05, w: 0.45, h: 0.45 });
  s.addText([
    { text: "Корпус — общественное достояние", options: { bold: true, breakLine: true } },
    { text: "«Преступление и наказание», «Идиот», «Бесы», «Фауст» строго в переводе Холодковского (современные переводы охраняются). ~650 тыс. слов.", options: {} },
  ], { x: 1.1, y: 0.98, w: 8.4, h: 1.1, fontSize: 13, color: INK });
  const step = (x, t) => {
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 2.25, w: 2.02, h: 0.72, rectRadius: 0.08, fill: { color: TINT }, shadow: shadow() });
    s.addText(t, { x, y: 2.25, w: 2.02, h: 0.72, align: "center", valign: "middle", fontSize: 11.5, color: INK, margin: 0.03 });
  };
  step(0.5, "скачивание\n(az.lib.ru)"); step(2.86, "очистка HTML\n(state-machine)");
  step(5.22, "разметка: часть,\nглава, сцена, реплика"); step(7.58, "чанкинг —\n3 стратегии");
  [2.56, 4.92, 7.28].forEach((x) => s.addText("→", { x, y: 2.33, w: 0.3, h: 0.5, fontSize: 18, color: ROSE, align: "center", margin: 0 }));
  s.addText("данные не в git — всё строится одним скриптом (bootstrap.py)", { x: 0.5, y: 3.1, w: 9, h: 0.35, fontSize: 11.5, italic: true, color: MUT, margin: 0 });
  const half = (x, ic, head, body) => {
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y: 3.6, w: 4.42, h: 1.55, rectRadius: 0.09, fill: { color: TINT }, shadow: shadow() });
    s.addImage({ data: icons[ic], x: x + 0.22, y: 3.82, w: 0.42, h: 0.42 });
    s.addText([{ text: head, options: { bold: true, breakLine: true, paraSpaceAfter: 4 } }, { text: body }],
      { x: x + 0.8, y: 3.72, w: 3.45, h: 1.35, fontSize: 12, color: INK });
  };
  half(0.5, "chart", "EDA → решения", "длины абзацев → параметры чанкинга; частоты имён → словарь 87 алиасов («Родя» → «Раскольников»)");
  half(5.08, "ok", "Eval: 120 вопросов", "по 30 на книгу (факты / цитаты / интерпретация); валидность всех 120 проверена программно против корпуса");
  s.addNotes("Корпус юридически чистый: общественное достояние, Фауст — именно в переводе Холодковского, современные переводы под охраной. Пайплайн данных воспроизводим одним скриптом. EDA не для галочки: из него параметры чанкинга и словарь алиасов. Eval — 120 вопросов, каждый программно верифицирован.");

  // ── 5. Архитектура ──────────────────────────────────────────────────────
  s = p.addSlide(); s.background = { color: WHITE };
  title(s, "Архитектура: гибридный retrieval + генерация с цитированием");
  const box = (x, y, w, t, fill = TINT, col = INK) => {
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.95, rectRadius: 0.08, fill: { color: fill }, shadow: shadow() });
    s.addText(t, { x, y, w, h: 0.95, align: "center", valign: "middle", fontSize: 11.5, color: col, margin: 0.04 });
  };
  box(0.5, 1.35, 1.62, "вопрос +\nнормализация имён");
  box(2.5, 1.35, 1.95, "BM25 + e5-base,\nслияние RRF\n→ топ-30");
  box(4.83, 1.35, 1.95, "reranker\nbge-v2-m3\n→ топ-6");
  box(7.16, 1.35, 2.3, "GigaChat: ответ\nс цитатой и адресом\nили отказ", BERRY, WHITE);
  [2.14, 4.47, 6.8].forEach((x) => s.addText("→", { x, y: 1.65, w: 0.35, h: 0.4, fontSize: 20, color: ROSE, align: "center", margin: 0 }));
  s.addText([
    { text: "Решения приняты по экспериментам (13 записей в docs/decisions.md):", options: { bold: true, breakLine: true, paraSpaceAfter: 8 } },
    { text: "индекс — файлы, без векторной БД: на 10⁴ чанков numpy-перебор быстрее инфраструктуры", options: { bullet: true, breakLine: true, paraSpaceAfter: 7 } },
    { text: "RRF вместо взвешенной суммы — не требует калибровки шкал BM25 и косинуса", options: { bullet: true, breakLine: true, paraSpaceAfter: 7 } },
    { text: "структурные вопросы («чем заканчивается?») — мимо similarity-поиска: срез конца книги; класс найден на живом демо и закрыт итерацией", options: { bullet: true, breakLine: true, paraSpaceAfter: 7 } },
    { text: "LLM за адаптером: GigaChat (кэш OAuth) или любой OpenAI-совместимый эндпоинт", options: { bullet: true } },
  ], { x: 0.5, y: 2.75, w: 9.0, h: 2.5, fontSize: 13, color: INK });
  s.addNotes("Пайплайн: нормализация алиасов, гибрид BM25 плюс эмбеддинги с RRF-слиянием, кросс-энкодер реранкер, генерация с обязательным цитированием. Каждое решение аргументировано и записано — например, отказ от векторной БД: на наших объёмах numpy быстрее. Отдельная история — структурные вопросы, класс отказов, найденный на живом демо и закрытый итерацией.");

  // ── 6. Эксперименты ─────────────────────────────────────────────────────
  s = p.addSlide(); s.background = { color: WHITE };
  title(s, "Эксперименты: чанкинг и реранкер на 120 вопросах");
  const th = (t) => ({ text: t, options: { fill: { color: BERRY }, color: WHITE, bold: true } });
  s.addTable([
    [th("Конфигурация"), th("span@1"), th("span@5"), th("MRR")],
    ["окна, гибрид BM25+e5", "0.23", "0.42", "0.32"],
    [{ text: "окна, гибрид + reranker", options: { bold: true, fill: { color: TINT } } },
     { text: "0.39", options: { bold: true, fill: { color: TINT } } },
     { text: "0.57", options: { bold: true, fill: { color: TINT } } },
     { text: "0.47", options: { bold: true, fill: { color: TINT } } }],
    ["абзацы, гибрид + reranker", "0.31", "0.45", "0.37"],
    ["главы, гибрид + reranker", "0.33", "0.59", "0.43"],
  ], { x: 0.5, y: 1.15, w: 5.7, colW: [2.9, 0.93, 0.93, 0.94], fontSize: 12,
       color: INK, border: { pt: 0.5, color: "D8CFC4" }, align: "center",
       margin: [0.04, 0.06, 0.04, 0.06] });
  s.addShape(p.shapes.ROUNDED_RECTANGLE, { x: 6.55, y: 1.15, w: 2.95, h: 2.25, rectRadius: 0.09, fill: { color: TINT }, shadow: shadow() });
  s.addText("+70 %", { x: 6.55, y: 1.45, w: 2.95, h: 0.9, align: "center", fontSize: 46, bold: true, color: OK, fontFace: "Cambria" });
  s.addText("к точности топ-1 даёт реранкер — самый выгодный компонент", { x: 6.75, y: 2.45, w: 2.55, h: 0.75, align: "center", fontSize: 12, color: INK });
  s.addText([
    { text: "span recall — в топ-k есть чанк с золотой подстрокой ответа", options: { bullet: true, breakLine: true, paraSpaceAfter: 7 } },
    { text: "«главы» выигрывают только размером чанка: в контекст LLM такой чанк не влезает — для продукта непригодно", options: { bullet: true, breakLine: true, paraSpaceAfter: 7 } },
    { text: "выбор: окна ~180 слов, не пересекающие границ глав", options: { bullet: true, bold: true } },
  ], { x: 0.5, y: 3.6, w: 9, h: 1.6, fontSize: 13, color: INK });
  s.addNotes("Три стратегии чанкинга сравнены на 120 вопросах. Реранкер — самое выгодное решение: плюс 70 процентов к точности первой позиции. Стратегия по главам красива в метрике recall, но это артефакт размера чанка — глава не влезает в контекст. Выбрали окна по 180 слов внутри глав.");

  // ── 7. Импакт ───────────────────────────────────────────────────────────
  s = p.addSlide(); s.background = { color: WHITE };
  title(s, "Импакт: тот же GigaChat — с RAG и без");
  const mk = (v, good) => ({ text: v, options: { bold: true, color: good ? OK : BAD } });
  s.addTable([
    [th("Метрика (29 вопросов)"), th("LLM без RAG"), th("ClassicLiteratureRAG")],
    ["Цитаты дословно из текста", mk("0 / 27", false), mk("8 / 9", true)],
    ["Существо ответа верно", "10 / 29", "11 / 29"],
    ["Верный номер главы", mk("2 / 15", false), mk("12 / 15", true)],
    ["Честные отказы вместо вымысла", "—", mk("9 / 29", true)],
  ], { x: 0.5, y: 1.15, w: 9.0, colW: [4.0, 2.3, 2.7], fontSize: 13, color: INK,
       border: { pt: 0.5, color: "D8CFC4" }, align: "center",
       margin: [0.05, 0.06, 0.05, 0.06] });
  s.addText([
    { text: "По существу — сопоставимо. Разница в другом: наш ответ ", options: {} },
    { text: "проверяем", options: { bold: true, color: BERRY } },
    { text: " — цитата дословна, адрес верен. Метрики автоматические (дословность по корпусу, леммная сверка, номер главы), сырые ответы сохранены для аудита, прогон воспроизводим.", options: {} },
  ], { x: 0.5, y: 3.75, w: 9, h: 1.3, fontSize: 14, color: INK });
  s.addNotes("Оценка импакта — измерение, а не опрос: тот же GigaChat с RAG и без на одних вопросах. По существу сопоставимо, но у baseline ноль дословных цитат из 27 — ответ непроверяем. У нас 8 из 9, верные главы и честные отказы. Все метрики автоматические, сырые ответы сохранены — любую цифру можно проверить в репозитории.");

  // ── 8. Инженерия, продукт, AI ───────────────────────────────────────────
  s = p.addSlide(); s.background = { color: WHITE };
  title(s, "Инженерия, продукт и AI-инструменты");
  const card = (x, y, w, h, ic, head, items) => {
    s.addShape(p.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.09, fill: { color: TINT }, shadow: shadow() });
    s.addImage({ data: icons[ic], x: x + 0.22, y: y + 0.2, w: 0.4, h: 0.4 });
    s.addText(head, { x: x + 0.75, y: y + 0.18, w: w - 0.9, h: 0.45, fontSize: 14.5, bold: true, color: INK, margin: 0 });
    s.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1, paraSpaceAfter: 3.5 } })),
      { x: x + 0.28, y: y + 0.7, w: w - 0.5, h: h - 0.85, fontSize: 11.5, color: INK });
  };
  card(0.5, 1.05, 4.42, 2.15, "cogs", "Инженерия", [
    "35 юнит-тестов без сети, ruff, CI (GitHub Actions)",
    "Docker c CPU-torch; деплой на HF Spaces одним скриптом",
    "готовый индекс через git-lfs — старт за секунды",
  ]);
  card(5.08, 1.05, 4.42, 2.15, "robot", "AI-инструменты", [
    "разработка в паре с Claude Code",
    "каждый шаг — в docs/ai_usage_log.md с проверкой результата",
    "13 дизайн-решений с аргументацией в docs/decisions.md",
  ]);
  card(0.5, 3.4, 4.42, 1.75, "fb", "Продукт живёт", [
    "MVP задеплоен, доступен жюри",
    "фидбек «помог / не помог» + комментарий → приватный HF-датасет",
  ]);
  card(5.08, 3.4, 4.42, 1.75, "search", "Итерация по фидбеку", [
    "живой отказ демо → класс структурных вопросов",
    "диагностика → фикс → метрики до/после (D-011)",
  ]);
  s.addNotes("Инженерия: тесты, CI, докер, деплой одним скриптом. AI-инструменты применялись открыто: каждый шаг с Claude Code зафиксирован в логе вместе со способом проверки. Продукт живой: MVP задеплоен, встроен сбор фидбека, и цикл итерации по реальному отказу демо уже пройден.");

  // ── 9. Финал ────────────────────────────────────────────────────────────
  s = p.addSlide(); s.background = { color: BERRY };
  s.addText("Проверяемые ответы по классике — уже работают", {
    x: 0.7, y: 0.55, w: 8.6, h: 0.6, align: "center", fontFace: "Cambria",
    fontSize: 28, bold: true, color: WHITE });
  const fin = (x, big, cap) => {
    s.addText(big, { x, y: 1.7, w: 2.8, h: 0.75, align: "center", valign: "middle",
      fontSize: 36, bold: true, color: CREAM, fontFace: "Cambria" });
    s.addText(cap, { x, y: 2.5, w: 2.8, h: 0.85, align: "center", valign: "top",
      fontSize: 12, color: "D9C7CE" });
  };
  fin(0.65, "8 / 9", "дословных цитат\n(у LLM без RAG — 0/27)");
  fin(3.6, "+70 %", "к точности retrieval\nот реранкера");
  fin(6.55, "650 тыс.", "слов в корпусе,\nготовом к расширению");
  s.addText([
    { text: "Дальше: атрибуция реплик персонажам · faithfulness-метрика LLM-судьёй · расширение корпуса", options: { breakLine: true, paraSpaceAfter: 12 } },
    { text: "Демо: huggingface.co/spaces/ArtemResearch/ClassicLiteratureRAG", options: { bold: true } },
  ], { x: 0.7, y: 3.65, w: 8.6, h: 1.0, align: "center", fontSize: 14, color: CREAM });
  s.addText("Спасибо! Вопросы?", { x: 0.7, y: 4.8, w: 8.6, h: 0.5, align: "center", fontSize: 18, bold: true, color: WHITE });
  s.addNotes("Итого: система с проверяемыми ответами уже задеплоена и работает. 8 из 9 дословных цитат против нуля у чистой LLM. Дальше — атрибуция реплик, faithfulness-метрика и расширение корпуса: пайплайн к этому готов. Спасибо, готов к вопросам!");

  await p.writeFile({ fileName: path.join(__dirname, "..", "docs", "presentation.pptx") });
  console.log("OK: docs/presentation.pptx");
})();
