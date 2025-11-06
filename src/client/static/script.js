// Estado del juego
let currentSuspectIndex = 0;
let chatHistory = [];
let suspects = [];
let characters = [];

// Elementos del DOM
const startScreen = document.getElementById('start-screen');
const gameScreen = document.getElementById('game-screen');
const victoryScreen = document.getElementById('victory-screen');
const defeatScreen = document.getElementById('defeat-screen');

const startBtn = document.getElementById('start-btn');
const backToStartBtn = document.getElementById('back-to-start');
const backFromVictoryBtn = document.getElementById('back-from-victory');
const backFromDefeatBtn = document.getElementById('back-from-defeat');
const restartFromVictoryBtn = document.getElementById('restart-from-victory');
const restartFromDefeatBtn = document.getElementById('restart-from-defeat');

const suspectAvatar = document.getElementById('suspect-avatar');
const suspectName = document.getElementById('suspect-name');
const suspectRole = document.getElementById('suspect-role');
const suspectNumber = document.getElementById('suspect-number');
const chatMessages = document.getElementById('chat-messages');
const questionInput = document.getElementById('question-input');
const sendBtn = document.getElementById('send-btn');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const solveBtn = document.getElementById('solve-btn');
const ws = new WebSocket("ws://localhost:8080/ws/game");
// Iniciar juego
startBtn.addEventListener('click', startGame);

backToStartBtn.addEventListener('click', goToStart);
backFromVictoryBtn.addEventListener('click', goToStart);
backFromDefeatBtn.addEventListener('click', goToStart);
restartFromVictoryBtn.addEventListener('click', startGame);
restartFromDefeatBtn.addEventListener('click', startGame);
let killer
suspects = [{"name":"Jack Domador", "role": 'Domador'},
                {"name":"Madame Seraphine", "role": 'Vidente'},
                {"name":"Mefisto Bombita", "role": 'Payaso'},
                {"name":"Silvana Funambula","role": 'Equilibrista'},
                {"name":"Ñopin Desfijo", "role": 'Director y maestro de ceremonias'}
    ]
// EVENTOS DEL WEB WebSocket
//
ws.onmessage = (event)=> {
  const data = JSON.parse(event.data)
  if (data.type == "intro") {
    
    console.log(suspects)
    characters = data.characters
    killer = data.killer
    console.log(killer)
  }else if (data.type == "answer"){
    addSuspectMessage(data.message)
  }

}
function startGame() {
    hideAllScreens();
    gameScreen.classList.add('active');
    currentSuspectIndex = 0;
    loadSuspect(currentSuspectIndex);
    
    }

function goToStart() {
    hideAllScreens();
    startScreen.classList.add('active');
}

function hideAllScreens() {
    startScreen.classList.remove('active');
    gameScreen.classList.remove('active');
    victoryScreen.classList.remove('active');
    defeatScreen.classList.remove('active');
}

// Cargar sospechoso
function loadSuspect(index) {
    const suspect = suspects[index];
    suspectName.textContent = suspect["name"];
    suspectRole.textContent = suspect["role"];
    suspectNumber.textContent = `${index + 1}/${suspects.length}`;
    
    // Actualizar botones de navegación
    prevBtn.disabled = index === 0;
    nextBtn.disabled = index === suspects.length - 1;
    
    // Limpiar chat
    chatMessages.innerHTML = '';
    
}

// Mensajes de bienvenida
function getWelcomeMessage(suspect) {
    const welcomes = {
        1: "Detective... Supongo que quiere interrogarme. Adelante.",
        2: "Ah, el detective. Las cartas ya me dijeron que vendría...",
        3: "¿Qué quiere saber? Hable rápido.",
        4: "D-detective... yo... no hice nada malo...",
        5: "Siéntese, detective. Hablemos de bestias y secretos.",
        6: "¡Detective! ¡Gracias por venir! ¡Tengo que contarle todo!"
    };
    return welcomes[suspect.id] || "Estoy listo para responder sus preguntas.";
}

// Enviar pregunta
function sendQuestion() {
    const question = questionInput.value.trim();
    if (!question) return;
    
    addDetectiveMessage(question);
    questionInput.value = '';
    console.log("Enviando mensaje...") 
    ws.send(`interrogar ${suspects[currentSuspectIndex].name}`)
    ws.send(question)
    // Simular tiempo de respuesta (como si la IA estuviera pensando)
    //const thinkingTime = 1500 + Math.random() * 1500;
    //setTimeout(() => {
        //const response = generateResponse(question);
        //addSuspectMessage(response);
    //}, thinkingTime);
}

// Generar respuesta del sospechoso
function generateResponse(question) {
    const suspect = suspects[currentSuspectIndex];
    const lowerQuestion = question.toLowerCase();
    
    // Buscar palabras clave en la pregunta
    for (const [keyword, response] of Object.entries(suspect.responses.keywords)) {
        if (lowerQuestion.includes(keyword)) {
            return response;
        }
    }
    
    // Respuesta por defecto aleatoria
    const defaultResponses = suspect.responses.default;
    return defaultResponses[Math.floor(Math.random() * defaultResponses.length)];
}

// Agregar mensaje del detective
function addDetectiveMessage(text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message detective';
    messageDiv.innerHTML = `
        <div class="message-label">🔍 DETECTIVE:</div>
        <div class="message-text">${text}</div>
    `;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Agregar mensaje del sospechoso
function addSuspectMessage(text) {
    const suspect = suspects[currentSuspectIndex];
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message suspect';
    messageDiv.innerHTML = `
        <div class="message-label">${suspect.avatar} ${suspect.name}:</div>
        <div class="message-text">${text}</div>
    `;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Agregar mensaje del sistema
function addSystemMessage(text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message suspect';
    messageDiv.style.borderColor = '#660000';
    messageDiv.style.color = '#660000';
    messageDiv.style.background = 'linear-gradient(135deg, #1a0000 0%, #0a0000 100%)';
    messageDiv.innerHTML = `
        <div class="message-label">🎪 SISTEMA:</div>
        <div class="message-text">${text}</div>
    `;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Resolver caso
function solveCase() {
    const suspectNames = suspects.map(s => s.name);
    const suspectList = suspectNames.map((name, i) => `\n${i + 1}. ${name}`).join('\n');
    
    Swal.fire({
            title: "¿Quien es el asesino?",
            icon:"question",
            text:suspectList,
            theme: 'dark',
            input: "text",
            inputAttributes: {autocapitalize: "off"},
            showCancelButton: true,
            confirmButtonText: "Resolver caso",
            showLoaderOnConfirm: true,
            customClass: {
              popup: 'sweetalert',
            },
            allowOutsideClick: () => !Swal.isLoading()
            }).then((result) => {
            if (result.isConfirmed) {
                choice = result.value
            }
          });   
    if (choice === null) return; // Usuario canceló
    
    const choiceNum = parseInt(choice);
    
    if (isNaN(choiceNum) || choiceNum < 1 || choiceNum > suspects.length) {
        alert('Número inválido. Intenta de nuevo.');
        return;
    }
    
    const chosenSuspect = suspects[choiceNum - 1];
    
    if (chosenSuspect.name == killer) {
        // Victoria
        hideAllScreens();
        victoryScreen.classList.add('active');
    } else {
        // Derrota
        hideAllScreens();
        defeatScreen.classList.add('active');
    }
}

// Event listeners
sendBtn.addEventListener('click', sendQuestion);
questionInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendQuestion();
    }
});

prevBtn.addEventListener('click', () => {
    if (currentSuspectIndex > 0) {
        currentSuspectIndex--;
        loadSuspect(currentSuspectIndex);
        addSystemMessage(`🔄 Cambiando a sospechoso ${currentSuspectIndex + 1} de ${suspects.length}`);
    }
});

nextBtn.addEventListener('click', () => {
    if (currentSuspectIndex < suspects.length - 1) {
        currentSuspectIndex++;
        loadSuspect(currentSuspectIndex);
        addSystemMessage(`🔄 Cambiando a sospechoso ${currentSuspectIndex + 1} de ${suspects.length}`);
    }
});

solveBtn.addEventListener('click', solveCase);


