const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// DOM Elements
const authView = document.getElementById('auth-view');
const appView = document.getElementById('app-view');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const tabLogin = document.getElementById('tab-login');
const tabRegister = document.getElementById('tab-register');
const authMessage = document.getElementById('auth-message');

const sidebarStudioName = document.getElementById('sidebar-studio-name');
const sidebarStudioEmail = document.getElementById('sidebar-studio-email');
const eventList = document.getElementById('event-list');
const newEventModal = document.getElementById('new-event-modal');

const emptyState = document.getElementById('empty-state');
const eventDetails = document.getElementById('event-details');
const detailTitle = document.getElementById('detail-title');
const detailDate = document.getElementById('detail-date');
const guestLinkInput = document.getElementById('guest-link-input');
const guestLinkBtn = document.getElementById('guest-link-btn');

const statTotal = document.getElementById('stat-total');
const statPeople = document.getElementById('stat-people');
const statPending = document.getElementById('stat-pending');
const statProcessed = document.getElementById('stat-processed');

const dropZone = document.getElementById('drop-zone');
const fileUpload = document.getElementById('file-upload');
const selectedFilesCount = document.getElementById('selected-files-count');
const btnUpload = document.getElementById('btn-upload');
const uploadProgressContainer = document.getElementById('upload-progress-container');
const uploadProgressBar = document.getElementById('upload-progress-bar');
const uploadPercentage = document.getElementById('upload-percentage');
const uploadStatusText = document.getElementById('upload-status-text');
const aiProcessingAlert = document.getElementById('ai-processing-alert');

// State
let currentUser = null;
let currentStudioId = null;
let currentEvent = null;
let selectedFiles = [];

// Initialization
async function init() {
    const { data: { session } } = await supabaseClient.auth.getSession();
    if (session) {
        await handleUserLogin(session.user);
    } else {
        showAuth();
    }

    supabaseClient.auth.onAuthStateChange(async (event, session) => {
        if (event === 'SIGNED_IN' && session) {
            await handleUserLogin(session.user);
        } else if (event === 'SIGNED_OUT') {
            showAuth();
        }
    });
}

// UI Toggles
function showAuth() {
    authView.classList.remove('hidden');
    appView.classList.add('hidden');
    currentUser = null;
    currentStudioId = null;
}

function showApp() {
    authView.classList.add('hidden');
    appView.classList.remove('hidden');
}

function switchAuthTab(tab) {
    authMessage.classList.add('hidden');
    if (tab === 'login') {
        loginForm.classList.remove('hidden');
        registerForm.classList.add('hidden');
        tabLogin.classList.add('bg-white', 'shadow', 'text-[#1a1c1c]');
        tabLogin.classList.remove('text-[#696868]', 'hover:text-[#1a1c1c]');
        tabRegister.classList.add('text-[#696868]', 'hover:text-[#1a1c1c]');
        tabRegister.classList.remove('bg-white', 'shadow', 'text-[#1a1c1c]');
    } else {
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
        tabRegister.classList.add('bg-white', 'shadow', 'text-[#1a1c1c]');
        tabRegister.classList.remove('text-[#696868]', 'hover:text-[#1a1c1c]');
        tabLogin.classList.add('text-[#696868]', 'hover:text-[#1a1c1c]');
        tabLogin.classList.remove('bg-white', 'shadow', 'text-[#1a1c1c]');
    }
}

function showMessage(elementId, msg, type = 'error') {
    const el = document.getElementById(elementId);
    el.textContent = msg;
    el.classList.remove('hidden', 'bg-red-100', 'text-red-700', 'bg-green-100', 'text-green-700', 'bg-yellow-100', 'text-yellow-700');
    if (type === 'error') el.classList.add('bg-red-100', 'text-red-700');
    else if (type === 'success') el.classList.add('bg-green-100', 'text-green-700');
    else if (type === 'warning') el.classList.add('bg-yellow-100', 'text-yellow-700');
}

function toggleNewEventModal(show) {
    if (show) {
        newEventModal.classList.remove('hidden');
    } else {
        newEventModal.classList.add('hidden');
        document.getElementById('new-event-title').value = '';
        document.getElementById('new-event-date').value = '';
    }
}

// Authentication
window.handleLogin = async function(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    document.getElementById('login-spinner').classList.remove('hidden');
    const { error } = await supabaseClient.auth.signInWithPassword({ email, password });
    document.getElementById('login-spinner').classList.add('hidden');
    
    if (error) {
        showMessage('auth-message', `Giriş başarısız: ${error.message}`);
        if (error.message.includes("Email not confirmed")) {
            showMessage('auth-message', 'E-posta henüz onaylanmadı. Lütfen gelen kutunuzu kontrol edin.', 'warning');
        }
    }
}

window.handleRegister = async function(e) {
    e.preventDefault();
    const name = document.getElementById('reg-name').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    
    document.getElementById('reg-spinner').classList.remove('hidden');
    const { error } = await supabaseClient.auth.signUp({
        email,
        password,
        options: { data: { studio_name: name } }
    });
    document.getElementById('reg-spinner').classList.add('hidden');
    
    if (error) {
        showMessage('auth-message', `Kayıt başarısız: ${error.message}`);
    } else {
        showMessage('auth-message', 'Kayıt başarılı! Lütfen giriş yapın (E-posta onayı gerekiyorsa onaylayın).', 'success');
        switchAuthTab('login');
    }
}

window.handleLogout = async function() {
    await supabaseClient.auth.signOut();
}

async function handleUserLogin(user) {
    currentUser = user;
    const studioName = user.user_metadata?.studio_name || "Stüdyo";
    
    // Get or Create Studio ID
    let { data: studios } = await supabaseClient.from('studios').select('id').eq('email', user.email);
    if (!studios || studios.length === 0) {
        const { data: newStudio } = await supabaseClient.from('studios').insert([{
            auth_id: user.id,
            name: studioName,
            email: user.email
        }]).select();
        currentStudioId = newStudio[0].id;
    } else {
        currentStudioId = studios[0].id;
    }

    sidebarStudioName.textContent = studioName;
    sidebarStudioEmail.textContent = user.email;
    
    showApp();
    loadEvents();
}

// Events
async function loadEvents() {
    const { data: events, error } = await supabaseClient
        .from('events')
        .select('*')
        .eq('studio_id', currentStudioId)
        .order('created_at', { ascending: false });

    if (error) {
        console.error("Error loading events:", error);
        return;
    }

    eventList.innerHTML = '';
    
    if (events.length === 0) {
        eventList.innerHTML = '<p class="text-xs text-[#696868] px-2">Henüz etkinlik oluşturmadınız.</p>';
    } else {
        events.forEach(ev => {
            const btn = document.createElement('button');
            btn.className = 'w-full text-left px-4 py-3 rounded-lg text-sm font-medium transition-colors hover:bg-[#f3f3f4] text-[#4b463d] truncate';
            btn.textContent = ev.title;
            btn.onclick = () => selectEvent(ev, btn);
            eventList.appendChild(btn);
        });
    }
}

window.handleCreateEvent = async function(e) {
    e.preventDefault();
    const title = document.getElementById('new-event-title').value;
    const date = document.getElementById('new-event-date').value;
    
    document.getElementById('create-event-spinner').classList.remove('hidden');
    const { data, error } = await supabaseClient.from('events').insert([{
        studio_id: currentStudioId,
        title: title,
        event_date: date
    }]).select();
    document.getElementById('create-event-spinner').classList.add('hidden');
    
    if (error) {
        alert("Oluşturulamadı: " + error.message);
    } else {
        toggleNewEventModal(false);
        await loadEvents();
        selectEvent(data[0]);
    }
}

function selectEvent(ev, btnElement = null) {
    currentEvent = ev;
    emptyState.classList.add('hidden');
    eventDetails.classList.remove('hidden');
    
    loadEventStats(ev.id);
    
    // Highlight sidebar button
    document.querySelectorAll('#event-list button').forEach(b => {
        b.classList.remove('bg-[#f0e0c8]', 'text-[#1a1c1c]', 'font-bold');
        b.classList.add('text-[#4b463d]', 'font-medium');
    });
    if (btnElement) {
        btnElement.classList.add('bg-[#f0e0c8]', 'text-[#1a1c1c]', 'font-bold');
        btnElement.classList.remove('text-[#4b463d]', 'font-medium');
    }

    detailTitle.textContent = ev.title;
    detailDate.textContent = new Date(ev.event_date).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' });
    
    // Guest Link (using current origin or local testing)
    // Note: To allow Vercel to work nicely, guest link should point to the domain where index.html is hosted.
    // Since we are deploying both to the same Vercel project, guest link is just the same domain.
    const guestUrl = `${window.location.origin}/?event_id=${ev.id}`;
    guestLinkInput.value = guestUrl;
    guestLinkBtn.href = guestUrl;

    // Reset upload UI
    selectedFiles = [];
    selectedFilesCount.textContent = '';
    btnUpload.classList.add('hidden');
    uploadProgressContainer.classList.add('hidden');
    aiProcessingAlert.classList.add('hidden');
    uploadProgressBar.style.width = '0%';
}

window.copyGuestLink = function() {
    guestLinkInput.select();
    document.execCommand('copy');
    const orig = guestLinkInput.nextElementSibling.textContent;
    guestLinkInput.nextElementSibling.textContent = 'Kopyalandı!';
    setTimeout(() => { guestLinkInput.nextElementSibling.textContent = orig; }, 2000);
}

window.handleDeleteEvent = async function() {
    if (!currentEvent) return;
    if (!confirm(`"${currentEvent.title}" etkinliğini ve tüm fotoğraflarını silmek istediğinize emin misiniz? Bu işlem geri alınamaz.`)) return;

    try {
        // Fotoğrafları al (storage'dan silmek için)
        const { data: photos, error: fetchError } = await supabaseClient
            .from('photos')
            .select('image_url')
            .eq('event_id', currentEvent.id);
        
        if (fetchError) throw fetchError;

        // Storage'dan dosyaları sil
        if (photos && photos.length > 0) {
            const filesToRemove = photos.map(p => {
                const parts = p.image_url.split('/');
                return parts[parts.length - 1];
            }).filter(Boolean);

            // Chunk by 100 to avoid request too large errors if there are many photos
            for (let i = 0; i < filesToRemove.length; i += 100) {
                const chunk = filesToRemove.slice(i, i + 100);
                await supabaseClient.storage.from('wedding_photos').remove(chunk);
            }
        }

        // DB'den fotoğrafları sil
        await supabaseClient.from('photos').delete().eq('event_id', currentEvent.id);
        
        // DB'den etkinliği sil
        const { error: deleteError } = await supabaseClient
            .from('events')
            .delete()
            .eq('id', currentEvent.id);
        
        if (deleteError) throw deleteError;

        alert("Etkinlik başarıyla silindi.");
        currentEvent = null;
        emptyState.classList.remove('hidden');
        eventDetails.classList.add('hidden');
        await loadEvents();
        
    } catch (err) {
        console.error("Silme hatası:", err);
        alert("Silinirken bir hata oluştu: " + err.message);
    }
}

// Event Stats Loader
async function loadEventStats(evId) {
    statTotal.textContent = '...';
    statPeople.textContent = '...';
    statPending.textContent = '...';
    statProcessed.textContent = '...';

    const { data: photos, error } = await supabaseClient
        .from('photos')
        .select('processed')
        .eq('event_id', evId);
    
    if (!error && photos) {
        const processedCount = photos.filter(p => p.processed).length;
        const pendingCount = photos.length - processedCount;
        statTotal.textContent = photos.length;
        statProcessed.textContent = processedCount;
        statPending.textContent = pendingCount;
    }

    try {
        const res = await fetch(`${GUEST_API_URL}/api/clusters/${evId}`);
        const data = await res.json();
        statPeople.textContent = data.clusters ? data.clusters.length : 0;
    } catch(err) {
        statPeople.textContent = '?';
    }
}

// File Uploads
window.handleFileSelect = function(e) {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
        selectedFiles = files;
        selectedFilesCount.textContent = `${files.length} fotoğraf seçildi`;
        btnUpload.classList.remove('hidden');
        uploadProgressContainer.classList.add('hidden');
        aiProcessingAlert.classList.add('hidden');
    }
}

// Drag and drop support
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('border-[#685d4a]', 'bg-[#f0e0c8]/20');
});
dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropZone.classList.remove('border-[#685d4a]', 'bg-[#f0e0c8]/20');
});
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('border-[#685d4a]', 'bg-[#f0e0c8]/20');
    if (e.dataTransfer.files.length > 0) {
        fileUpload.files = e.dataTransfer.files;
        window.handleFileSelect({ target: { files: e.dataTransfer.files } });
    }
});

// Resize Image Utility
function resizeImage(file, maxSize) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                let width = img.width;
                let height = img.height;

                if (width > height) {
                    if (width > maxSize) {
                        height *= maxSize / width;
                        width = maxSize;
                    }
                } else {
                    if (height > maxSize) {
                        width *= maxSize / height;
                        height = maxSize;
                    }
                }

                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);

                canvas.toBlob((blob) => {
                    resolve(new File([blob], file.name.replace(/\.[^/.]+$/, ".jpg"), {
                        type: 'image/jpeg',
                        lastModified: Date.now()
                    }));
                }, 'image/jpeg', 0.85);
            };
            img.onerror = reject;
            img.src = e.target.result;
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

window.startUpload = async function() {
    if (selectedFiles.length === 0) return;
    
    btnUpload.classList.add('hidden');
    uploadProgressContainer.classList.remove('hidden');
    aiProcessingAlert.classList.add('hidden');
    
    let successCount = 0;
    const totalFiles = selectedFiles.length;

    for (let i = 0; i < totalFiles; i++) {
        const file = selectedFiles[i];
        
        uploadStatusText.textContent = `Yükleniyor (${i + 1}/${totalFiles}). Sıkıştırılıyor...`;
        const percent = Math.round((i / totalFiles) * 100);
        uploadPercentage.textContent = `${percent}%`;
        uploadProgressBar.style.width = `${percent}%`;

        try {
            const resizedFile = await resizeImage(file, 1920);
            const fileName = `${crypto.randomUUID()}.jpg`;
            
            // Upload to storage
            const { error: uploadError } = await supabaseClient.storage.from('wedding_photos').upload(fileName, resizedFile);
            if (uploadError) throw uploadError;

            // Get public URL
            const { data: publicUrlData } = supabaseClient.storage.from('wedding_photos').getPublicUrl(fileName);
            
            // Insert into photos table
            const { error: dbError } = await supabaseClient.from('photos').insert([{
                event_id: currentEvent.id,
                image_url: publicUrlData.publicUrl
            }]);
            
            if (dbError) throw dbError;
            successCount++;
        } catch (err) {
            console.error(`Hata (${file.name}):`, err);
        }
    }

    uploadPercentage.textContent = `100%`;
    uploadProgressBar.style.width = `100%`;
    uploadStatusText.textContent = `✅ ${successCount} fotoğraf yüklendi!`;

    // İstatistikleri güncelle
    loadEventStats(currentEvent.id);

    // Trigger Worker via Guest API
    triggerWorker();
}

async function triggerWorker() {
    aiProcessingAlert.classList.remove('hidden');
    try {
        const triggerUrl = `${GUEST_API_URL}/api/trigger_worker`;
        await fetch(triggerUrl, { method: 'POST' });
    } catch (err) {
        console.error("Worker tetikleme hatası:", err);
    }
}

// Global scope bindings for HTML onClick events
window.switchAuthTab = switchAuthTab;
window.toggleNewEventModal = toggleNewEventModal;

// Start
init();
