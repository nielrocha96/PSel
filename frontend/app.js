// Código JS para upload de arquivo e perguntas

// =========================
// Declaração de variáveis globais
// =========================
let sessionId = null;                          // Armazena o ID da sessão retornado pelo backend
const backendUrl = "http://localhost:8000";    // URL base do backend (FastAPI)

const fileInput = document.getElementById("fileInput");   // Campo de upload de arquivo
const uploadBtn = document.getElementById("uploadBtn");   // Botão de enviar arquivo
const chatBox = document.getElementById("chat-box");      // Caixa onde aparecem as mensagens do chat
const questionInput = document.getElementById("question");// Campo de texto da pergunta
const askBtn = document.getElementById("askBtn");         // Botão de enviar pergunta


// =========================
// Função para adicionar mensagens ao chat
// =========================
function addMessage(sender, text) {
  const msg = document.createElement("div");   // Cria um novo elemento <div> para a mensagem
  msg.classList.add("msg", sender);            // Adiciona classes CSS: "msg" e o tipo (user/bot)
  msg.textContent = text;                      // Define o texto da mensagem
  chatBox.appendChild(msg);                    // Adiciona a mensagem ao final da caixa de chat
  chatBox.scrollTop = chatBox.scrollHeight;    // Faz o chat rolar automaticamente até o final
}


// =========================
// Função que exibe "Digitando..." (simula o bot escrevendo)
// =========================
function addTyping() {
  const msg = document.createElement("div");
  msg.classList.add("msg", "bot");             // Cria uma mensagem do tipo "bot"
  msg.id = "typing";                           // Define um ID fixo para poder removê-la depois
  msg.textContent = "Digitando...";            // Texto exibido enquanto espera a resposta
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;    // Mantém a rolagem no final
}

// =========================
// Remove o aviso "Digitando..." quando a resposta chega
// =========================
function removeTyping() {
  const t = document.getElementById("typing"); // Busca o elemento com id="typing"
  if (t) t.remove();                           // Se existir, remove do DOM
}


// =========================
// EVENTO: Enviar arquivo Excel
// =========================
uploadBtn.addEventListener("click", async () => {
  const file = fileInput.files[0];             // Pega o primeiro arquivo selecionado
  if (!file) return alert("Selecione um arquivo .xlsx primeiro!"); // Valida que há um arquivo

  addMessage("user", `Enviando arquivo: ${file.name}`); // Mostra a ação no chat
  const formData = new FormData();             // Cria um FormData (para enviar o arquivo)
  formData.append("file", file);               // Adiciona o arquivo sob a chave "file"

  try {
    // Faz o envio para o endpoint /upload
    const res = await fetch(`${backendUrl}/upload`, { method: "POST", body: formData });

    // Se a resposta não for OK, mostra erro
    if (!res.ok) {
      const err = await res.text();
      addMessage("bot", "Erro: " + err);
      return;
    }

    const data = await res.json();             // Converte a resposta para JSON
    if (!data.columns) {                       // Verifica se o backend retornou colunas
      addMessage("bot", "Erro inesperado do servidor.");
      return;
    }

    // Guarda o session_id e mostra feedback
    sessionId = data.session_id;
    addMessage("bot", `Arquivo recebido! Colunas: ${data.columns.join(", ")}`);
  }
  catch (err) {
    console.error(err);
    addMessage("bot", "Falha ao enviar arquivo."); // Em caso de erro de rede ou CORS
  }
});


// =========================
// EVENTO: Enviar pergunta ao backend
// =========================
askBtn.addEventListener("click", async () => {
  const question = questionInput.value.trim(); // Pega o texto e remove espaços extras
  if (!question) return;                       // Ignora se estiver vazio
  if (!sessionId) return alert("Envie um arquivo primeiro!"); // Garante que há sessão ativa

  addMessage("user", question);                // Mostra a pergunta no chat
  questionInput.value = "";                    // Limpa o campo
  addTyping();                                 // Exibe "Digitando..."

  try {
    // Faz a requisição POST ao endpoint /ask
    const res = await fetch(`${backendUrl}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, question }), // Envia pergunta + sessão
    });

    removeTyping();                            // Remove o "Digitando..."

    // Se houver erro HTTP, exibe no chat
    if (!res.ok) {
      const err = await res.text();
      addMessage("bot", "Erro: " + err);
      return;
    }

    const data = await res.json();             // Converte resposta em JSON
    addMessage("bot", data.answer);            // Mostra a resposta do backend no chat
  }
  catch (err) {
    removeTyping();
    console.error(err);
    addMessage("bot", "Falha na comunicação."); // Erro genérico de rede ou servidor
  }
});


// =========================
// Permitir enviar pergunta com Enter (sem clicar no botão)
// =========================
questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {     // Detecta a tecla Enter
    e.preventDefault();        // Evita que o Enter insira uma nova linha
    askBtn.click();            // Simula o clique do botão "Perguntar"
  }
});
