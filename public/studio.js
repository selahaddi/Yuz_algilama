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
const editEventModal = document.getElementById('edit-event-modal');
const orderDetailsModal = document.getElementById('order-details-modal');

const emptyState = document.getElementById('empty-state');
const eventDetails = document.getElementById('event-details');
const detailTitle = document.getElementById('detail-title');
const detailDate = document.getElementById('detail-date');
const guestLinkInput = document.getElementById('guest-link-input');
const guestLinkBtn = document.getElementById('guest-link-btn');
const detailStatus = document.getElementById('detail-status');

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
let currentStudioSettings = {};
let currentEvent = null;
let currentEventFilter = 'active';
let selectedFiles = [];
let uploadQueue = [];
let isUploadPaused = false;
let uploadIndex = 0;
let qrCodeObj = null;

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
    currentEvent = null;
    
    // UI Reset (Hesap değiştirince eski verilerin görünmemesi için)
    if(emptyState && eventDetails) {
        emptyState.classList.remove('hidden');
        eventDetails.classList.add('hidden');
    }
    
    // Dashboard Reset
    document.getElementById('dash-total-revenue').textContent = '0 TL';
    document.getElementById('dash-active-events').textContent = '0';
    document.getElementById('dash-pending-orders').textContent = '0';
    document.getElementById('dash-recent-orders').innerHTML = '<p class="text-sm text-[#696868]">Henüz sipariş yok.</p>';
    document.getElementById('notification-dot').classList.add('hidden');
    
    const ordersContainer = document.getElementById('orders-list-container');
    if(ordersContainer) ordersContainer.innerHTML = '';
}

function showApp() {
    authView.classList.add('hidden');
    appView.classList.remove('hidden');
    if (typeof switchTab === 'function') {
        switchTab('dashboard');
    }
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

function toggleEditEventModal(show) {
    if (show && currentEvent) {
        document.getElementById('edit-event-title').value = currentEvent.title;
        document.getElementById('edit-event-date').value = currentEvent.event_date;
        document.getElementById('edit-event-price').value = currentEvent.price_per_photo || 0;
        editEventModal.classList.remove('hidden');
    } else {
        editEventModal.classList.add('hidden');
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
    let { data: studios } = await supabaseClient.from('studios').select('*').eq('email', user.email);
    if (!studios || studios.length === 0) {
        const { data: newStudio } = await supabaseClient.from('studios').insert([{
            auth_id: user.id,
            name: studioName,
            email: user.email
        }]).select();
        currentStudioId = newStudio[0].id;
        currentStudioSettings = newStudio[0];
    } else {
        currentStudioId = studios[0].id;
        currentStudioSettings = studios[0];
    }

    sidebarStudioName.textContent = studioName;
    sidebarStudioEmail.textContent = user.email;
    
    showApp();
    loadEvents('active');
    fetchDashboardStats();
}

// Events
window.loadEvents = async function(status = 'active') {
    currentEventFilter = status;
    if (!currentStudioId) return;
    
    // UI Update for filters
    const btnActive = document.getElementById('filter-active');
    const btnArchived = document.getElementById('filter-archived');
    
    if(status === 'active') {
        btnActive.className = "text-xs font-bold text-[#685d4a]";
        btnArchived.className = "text-xs text-[#696868] hover:text-[#685d4a]";
    } else {
        btnArchived.className = "text-xs font-bold text-[#685d4a]";
        btnActive.className = "text-xs text-[#696868] hover:text-[#685d4a]";
    }

    const { data: events, error } = await supabaseClient
        .from('events')
        .select('*')
        .eq('studio_id', currentStudioId)
        .eq('status', status)
        .order('created_at', { ascending: false });

    if (error) {
        console.error("Error loading events:", error);
        return;
    }

    eventList.innerHTML = '';
    
    if (events.length === 0) {
        eventList.innerHTML = `<p class="text-xs text-[#696868] px-2">Henüz ${status === 'active' ? 'aktif' : 'arşivlenmiş'} etkinlik yok.</p>`;
    } else {
        events.forEach(ev => {
            const btn = document.createElement('button');
            btn.className = 'w-full text-left px-4 py-3 rounded-lg text-sm font-medium transition-colors hover:bg-[#f3f3f4] text-[#4b463d] truncate';
            btn.textContent = ev.title;
            btn.onclick = () => selectEvent(ev, btn);
            // Highlight if current
            if (currentEvent && currentEvent.id === ev.id) {
                btn.classList.add('bg-[#f0e0c8]', 'text-[#1a1c1c]', 'font-bold');
                btn.classList.remove('text-[#4b463d]', 'font-medium');
            }
            eventList.appendChild(btn);
        });
    }
}

window.handleCreateEvent = async function(e) {
    e.preventDefault();
    const title = document.getElementById('new-event-title').value;
    const date = document.getElementById('new-event-date').value;
    const price = parseFloat(document.getElementById('new-event-price').value) || 0;
    
    document.getElementById('create-event-spinner').classList.remove('hidden');
    const { data, error } = await supabaseClient.from('events').insert([{
        studio_id: currentStudioId,
        title: title,
        event_date: date,
        price_per_photo: price,
        status: 'active'
    }]).select();
    document.getElementById('create-event-spinner').classList.add('hidden');
    
    if (error) {
        alert("Oluşturulamadı: " + error.message);
    } else {
        toggleNewEventModal(false);
        await loadEvents('active');
        switchTab('events');
        selectEvent(data[0]);
        fetchDashboardStats();
    }
}

window.handleSaveEditEvent = async function(e) {
    e.preventDefault();
    if (!currentEvent) return;
    
    const title = document.getElementById('edit-event-title').value;
    const date = document.getElementById('edit-event-date').value;
    const price = parseFloat(document.getElementById('edit-event-price').value) || 0;
    
    document.getElementById('edit-event-spinner').classList.remove('hidden');
    const { error } = await supabaseClient.from('events').update({
        title: title,
        event_date: date,
        price_per_photo: price
    }).eq('id', currentEvent.id);
    document.getElementById('edit-event-spinner').classList.add('hidden');
    
    if (error) {
        alert("Güncellenemedi: " + error.message);
    } else {
        toggleEditEventModal(false);
        currentEvent.title = title;
        currentEvent.event_date = date;
        currentEvent.price_per_photo = price;
        detailTitle.textContent = title;
        detailDate.textContent = new Date(date).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' });
        await loadEvents(currentEventFilter);
    }
}

function selectEvent(ev, btnElement = null) {
    currentEvent = ev;
    emptyState.classList.add('hidden');
    eventDetails.classList.remove('hidden');
    
    loadEventStats(ev.id);
    switchEventTab('overview');
    
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
    
    if (ev.status === 'archived') {
        detailStatus.textContent = 'Arşivlendi';
        detailStatus.className = 'mt-2 inline-block px-2 py-1 text-xs font-bold rounded-md bg-gray-100 text-gray-700';
        document.getElementById('txt-archive-event').textContent = 'Aktif Yap';
    } else {
        detailStatus.textContent = 'Aktif';
        detailStatus.className = 'mt-2 inline-block px-2 py-1 text-xs font-bold rounded-md bg-green-100 text-green-700';
        document.getElementById('txt-archive-event').textContent = 'Arşivle';
    }
    
    const guestUrl = `${FRONTEND_URL}/?event_id=${ev.id}`;
    guestLinkInput.value = guestUrl;
    guestLinkBtn.href = guestUrl;

    // Reset upload UI
    selectedFiles = [];
    uploadQueue = [];
    isUploadPaused = false;
    uploadIndex = 0;
    selectedFilesCount.textContent = '';
    btnUpload.classList.add('hidden');
    document.getElementById('btn-pause').classList.add('hidden');
    document.getElementById('btn-resume').classList.add('hidden');
    uploadProgressContainer.classList.add('hidden');
    aiProcessingAlert.classList.add('hidden');
    uploadProgressBar.style.width = '0%';
}

window.handleArchiveEvent = async function() {
    if (!currentEvent) return;
    const newStatus = currentEvent.status === 'active' ? 'archived' : 'active';
    const actionText = newStatus === 'archived' ? 'arşivlemek' : 'aktif hale getirmek';
    
    if (!confirm(`Bu etkinliği ${actionText} istediğinize emin misiniz?`)) return;

    try {
        const { error } = await supabaseClient.from('events').update({ status: newStatus }).eq('id', currentEvent.id);
        if (error) throw error;
        
        currentEvent = null;
        emptyState.classList.remove('hidden');
        eventDetails.classList.add('hidden');
        await loadEvents(currentEventFilter);
        fetchDashboardStats();
    } catch (err) {
        alert("İşlem başarısız: " + err.message);
    }
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
        const { data: photos, error: fetchError } = await supabaseClient.from('photos').select('image_url').eq('event_id', currentEvent.id);
        if (fetchError) throw fetchError;

        if (photos && photos.length > 0) {
            const filesToRemove = photos.map(p => {
                const parts = p.image_url.split('/');
                return parts[parts.length - 1];
            }).filter(Boolean);

            for (let i = 0; i < filesToRemove.length; i += 100) {
                const chunk = filesToRemove.slice(i, i + 100);
                await supabaseClient.storage.from('wedding_photos').remove(chunk);
            }
        }

        await supabaseClient.from('photos').delete().eq('event_id', currentEvent.id);
        const { error: deleteError } = await supabaseClient.from('events').delete().eq('id', currentEvent.id);
        
        if (deleteError) throw deleteError;

        alert("Etkinlik başarıyla silindi.");
        currentEvent = null;
        emptyState.classList.remove('hidden');
        eventDetails.classList.add('hidden');
        await loadEvents(currentEventFilter);
        fetchDashboardStats();
        
    } catch (err) {
        console.error("Silme hatası:", err);
        alert("Silinirken bir hata oluştu: " + err.message);
    }
}

// Event Tabs (Overview / Gallery)
window.switchEventTab = function(tab) {
    if(tab === 'overview') {
        document.getElementById('event-tab-overview').className = "py-2 px-1 border-b-2 border-[#685d4a] text-[#1a1c1c] font-bold text-sm";
        document.getElementById('event-tab-gallery').className = "py-2 px-1 border-b-2 border-transparent text-[#696868] hover:text-[#1a1c1c] font-medium text-sm transition-colors";
        document.getElementById('event-overview-section').classList.remove('hidden');
        document.getElementById('event-gallery-section').classList.add('hidden');
    } else {
        document.getElementById('event-tab-gallery').className = "py-2 px-1 border-b-2 border-[#685d4a] text-[#1a1c1c] font-bold text-sm";
        document.getElementById('event-tab-overview').className = "py-2 px-1 border-b-2 border-transparent text-[#696868] hover:text-[#1a1c1c] font-medium text-sm transition-colors";
        document.getElementById('event-gallery-section').classList.remove('hidden');
        document.getElementById('event-overview-section').classList.add('hidden');
        fetchEventPhotos();
    }
}

// Event Stats Loader
async function loadEventStats(evId) {
    statTotal.textContent = '...';
    statPeople.textContent = '...';
    statPending.textContent = '...';
    statProcessed.textContent = '...';

    const { data: photos, error } = await supabaseClient.from('photos').select('processed').eq('event_id', evId);
    
    if (!error && photos) {
        const processedCount = photos.filter(p => p.processed).length;
        const pendingCount = photos.length - processedCount;
        statTotal.textContent = photos.length;
        statProcessed.textContent = processedCount;
        statPending.textContent = pendingCount;
        document.getElementById('gallery-count').textContent = photos.length;
    }

    const { data: orders, error: orderError } = await supabaseClient.from('orders').select('*').eq('event_id', evId).eq('status', 'pending');
    
    if (!orderError && orders) {
        document.getElementById('stat-orders').textContent = orders.length;
    }

    try {
        const res = await fetch(`${GUEST_API_URL}/api/clusters/${evId}`);
        const data = await res.json();
        statPeople.textContent = data.clusters ? data.clusters.length : 0;
    } catch(err) {
        statPeople.textContent = '?';
    }
}

// Event Gallery
window.fetchEventPhotos = async function() {
    if (!currentEvent) return;
    const grid = document.getElementById('gallery-grid');
    const loader = document.getElementById('gallery-loading');
    
    grid.innerHTML = '';
    loader.classList.remove('hidden');

    const { data: photos, error } = await supabaseClient.from('photos').select('*').eq('event_id', currentEvent.id).order('created_at', { ascending: false });
    
    loader.classList.add('hidden');
    
    if (error || !photos || photos.length === 0) {
        grid.innerHTML = '<p class="col-span-full text-sm text-[#696868]">Henüz fotoğraf yüklenmemiş.</p>';
        return;
    }
    
    document.getElementById('gallery-count').textContent = photos.length;
    
    photos.forEach(photo => {
        const div = document.createElement('div');
        div.className = 'relative group aspect-square rounded-xl overflow-hidden bg-gray-200 border border-[#e2e2e2]';
        div.innerHTML = `
            <img src="${photo.thumbnail_url || photo.image_url}" class="w-full h-full object-cover">
            <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-2">
                <button onclick="window.open('${photo.image_url}', '_blank')" class="bg-white text-[#1a1c1c] text-xs font-bold px-3 py-1 rounded hover:bg-[#f3f3f4]">Büyük Gör</button>
                <button onclick="deletePhoto('${photo.id}', '${photo.image_url}')" class="bg-red-600 text-white text-xs font-bold px-3 py-1 rounded hover:bg-red-700 flex items-center gap-1">
                    <span class="material-symbols-outlined text-[14px]">delete</span> Sil
                </button>
            </div>
        `;
        grid.appendChild(div);
    });
}

window.deletePhoto = async function(photoId, imageUrl) {
    if (!confirm("Bu fotoğrafı tamamen silmek istediğinize emin misiniz? (Sepetlerde varsa hata oluşturabilir)")) return;
    
    try {
        const parts = imageUrl.split('/');
        const filename = parts[parts.length - 1];
        if (filename) {
            await supabaseClient.storage.from('wedding_photos').remove([filename]);
        }
        await supabaseClient.from('photos').delete().eq('id', photoId);
        
        fetchEventPhotos();
        loadEventStats(currentEvent.id);
    } catch(err) {
        alert("Fotoğraf silinemedi: " + err.message);
    }
}


// File Uploads
window.handleFileSelect = function(e) {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
        selectedFiles = files;
        uploadQueue = files;
        uploadIndex = 0;
        isUploadPaused = false;
        selectedFilesCount.textContent = `${files.length} fotoğraf seçildi`;
        btnUpload.classList.remove('hidden');
        document.getElementById('btn-pause').classList.add('hidden');
        document.getElementById('btn-resume').classList.add('hidden');
        uploadProgressContainer.classList.add('hidden');
        aiProcessingAlert.classList.add('hidden');
    }
}

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

// Advanced Watermark logic integrated in resizeImage
function resizeImage(file, maxSize) {
    return new Promise((resolve, reject) => {
        // blueimp-load-image kütüphanesi kullanarak EXIF rotasyonunu düzeltiyoruz
        window.loadImage(
            file,
            async function (canvas) {
                if (canvas.type === 'error') {
                    reject(new Error("Resim okunamadı veya yüklenemedi."));
                    return;
                }

                // applyWatermarkToCanvas iptal edildi, orijinal resmi yüklüyoruz.

                canvas.toBlob((blob) => {
                    resolve(new File([blob], file.name.replace(/\.[^/.]+$/, ".jpg"), {
                        type: 'image/jpeg',
                        lastModified: Date.now()
                    }));
                }, 'image/jpeg', 0.85);
            },
            {
                maxWidth: maxSize,
                maxHeight: maxSize,
                canvas: true,
                meta: true, // EXIF verisini oku
                orientation: true // EXIF bilgisine göre resmi otomatik döndür
            }
        );
    });
}

// Function to apply watermark, used by both uploader and preview
async function applyWatermarkToCanvas(ctx, width, height, settings = null) {
    const s = settings || currentStudioSettings;
    if (!s) return;

    const opacity = s.watermark_opacity !== undefined ? parseFloat(s.watermark_opacity) : 0.6;
    const sizeRatio = s.watermark_size !== undefined ? parseFloat(s.watermark_size) : 0.05;
    const angleDegree = s.watermark_angle !== undefined ? parseFloat(s.watermark_angle) : 0;
    
    ctx.globalAlpha = opacity;
    const angleRadian = angleDegree * Math.PI / 180;
    
    ctx.translate(width / 2, height / 2);
    ctx.rotate(angleRadian);

    if (s.logo_url && s.logo_url.trim() !== '') {
        try {
            const logo = new Image();
            logo.crossOrigin = "anonymous";
            await new Promise((res, rej) => {
                logo.onload = res;
                logo.onerror = rej;
                logo.src = s.logo_url;
            });
            // Fit logo width to sizeRatio * canvas width
            const logoWidth = width * (sizeRatio * 5); // multiplier to make slider feel right
            const logoHeight = logo.height * (logoWidth / logo.width);
            ctx.drawImage(logo, -logoWidth / 2, -logoHeight / 2, logoWidth, logoHeight);
        } catch (e) {
            console.error("Logo load error", e);
            drawTextWatermark(ctx, width, s.watermark_text || "Stüdyo", sizeRatio);
        }
    } else if (s.watermark_text && s.watermark_text.trim() !== '') {
        drawTextWatermark(ctx, width, s.watermark_text, sizeRatio);
    }

    ctx.rotate(-angleRadian);
    ctx.translate(-width / 2, -height / 2);
    ctx.globalAlpha = 1.0;
}

function drawTextWatermark(ctx, width, text, sizeRatio) {
    const fontSize = Math.max(12, Math.floor(width * sizeRatio * 2)); // multiplier for text
    ctx.fillStyle = "#ffffff";
    ctx.font = `bold ${fontSize}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    
    ctx.shadowColor = "rgba(0, 0, 0, 0.5)";
    ctx.shadowBlur = 4;
    ctx.shadowOffsetX = 2;
    ctx.shadowOffsetY = 2;
    
    ctx.fillText(text, 0, 0);
    
    ctx.shadowColor = "transparent";
    ctx.strokeStyle = "rgba(0,0,0,0.3)";
    ctx.lineWidth = Math.max(1, fontSize / 20);
    ctx.strokeText(text, 0, 0);
}

window.startUpload = async function() {
    if (uploadQueue.length === 0) return;
    
    btnUpload.classList.add('hidden');
    document.getElementById('btn-pause').classList.remove('hidden');
    uploadProgressContainer.classList.remove('hidden');
    aiProcessingAlert.classList.add('hidden');
    
    processUploadQueue();
}

window.pauseUpload = function() {
    isUploadPaused = true;
    document.getElementById('btn-pause').classList.add('hidden');
    document.getElementById('btn-resume').classList.remove('hidden');
    uploadStatusText.textContent = `Yükleme Duraklatıldı (${uploadIndex}/${uploadQueue.length})`;
}

window.resumeUpload = function() {
    isUploadPaused = false;
    document.getElementById('btn-resume').classList.add('hidden');
    document.getElementById('btn-pause').classList.remove('hidden');
    processUploadQueue();
}

async function processUploadQueue() {
    const totalFiles = uploadQueue.length;

    while (uploadIndex < totalFiles && !isUploadPaused) {
        const file = uploadQueue[uploadIndex];
        
        uploadStatusText.textContent = `Yükleniyor (${uploadIndex + 1}/${totalFiles})...`;
        const percent = Math.round((uploadIndex / totalFiles) * 100);
        uploadPercentage.textContent = `${percent}%`;
        uploadProgressBar.style.width = `${percent}%`;

        try {
            const thumbnailFile = await resizeImage(file, 1024);
            const fileName = `${crypto.randomUUID()}`;
            
            await supabaseClient.storage.from('wedding_photos').upload(`${fileName}_thumb.jpg`, thumbnailFile);
            const { data: thumbData } = supabaseClient.storage.from('wedding_photos').getPublicUrl(`${fileName}_thumb.jpg`);
            
            const { error: dbError } = await supabaseClient.from('photos').insert([{
                event_id: currentEvent.id,
                image_url: thumbData.publicUrl, 
                thumbnail_url: thumbData.publicUrl 
            }]);
            
            if (dbError) throw dbError;
        } catch (err) {
            console.error(`Hata (${file.name}):`, err);
        }
        
        uploadIndex++;
    }

    if (uploadIndex >= totalFiles) {
        uploadPercentage.textContent = `100%`;
        uploadProgressBar.style.width = `100%`;
        uploadStatusText.textContent = `✅ ${totalFiles} fotoğraf yüklendi!`;
        document.getElementById('btn-pause').classList.add('hidden');
        
        if(currentEvent) loadEventStats(currentEvent.id);
        if(document.getElementById('event-gallery-section').classList.contains('hidden') === false) fetchEventPhotos();
        
        triggerWorker();
    }
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

// Settings Modal Logic
window.toggleSettingsModal = function(show) {
    const modal = document.getElementById('settings-modal');
    if (show) {
        document.getElementById('settings-color').value = currentStudioSettings?.primary_color || '#685d4a';
        document.getElementById('settings-color-picker').value = currentStudioSettings?.primary_color || '#685d4a';
        document.getElementById('settings-logo').value = currentStudioSettings?.logo_url || '';
        document.getElementById('settings-watermark').value = currentStudioSettings?.watermark_text || '';
        document.getElementById('settings-opacity').value = currentStudioSettings?.watermark_opacity ?? 0.6;
        document.getElementById('settings-size').value = currentStudioSettings?.watermark_size ?? 0.05;
        document.getElementById('settings-angle').value = currentStudioSettings?.watermark_angle ?? 0;
        
        document.getElementById('val-opacity').textContent = document.getElementById('settings-opacity').value;
        document.getElementById('val-size').textContent = document.getElementById('settings-size').value;
        document.getElementById('val-angle').textContent = document.getElementById('settings-angle').value + '°';
        
        updateWatermarkPreview();
        modal.classList.remove('hidden');
    } else {
        modal.classList.add('hidden');
    }
}

document.getElementById('settings-color-picker').addEventListener('input', (e) => {
    document.getElementById('settings-color').value = e.target.value.toUpperCase();
});
document.getElementById('settings-color').addEventListener('input', (e) => {
    if(/^#[0-9A-F]{6}$/i.test(e.target.value)) {
        document.getElementById('settings-color-picker').value = e.target.value;
    }
});

window.updateWatermarkPreview = async function() {
    const canvas = document.getElementById('watermark-preview-canvas');
    if(!canvas) return;
    
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Create temporary settings object
    const tempSettings = {
        logo_url: document.getElementById('settings-logo').value,
        watermark_text: document.getElementById('settings-watermark').value,
        watermark_opacity: document.getElementById('settings-opacity').value,
        watermark_size: document.getElementById('settings-size').value,
        watermark_angle: document.getElementById('settings-angle').value
    };
    
    await applyWatermarkToCanvas(ctx, canvas.width, canvas.height, tempSettings);
}

window.handleUpdateSettings = async function(e) {
    e.preventDefault();
    const primary_color = document.getElementById('settings-color').value;
    const logo_url = document.getElementById('settings-logo').value;
    const watermark_text = document.getElementById('settings-watermark').value;
    const watermark_opacity = parseFloat(document.getElementById('settings-opacity').value);
    const watermark_size = parseFloat(document.getElementById('settings-size').value);
    const watermark_angle = parseFloat(document.getElementById('settings-angle').value);
    
    document.getElementById('settings-spinner').classList.remove('hidden');
    const { error } = await supabaseClient.from('studios').update({
        primary_color, 
        logo_url, 
        watermark_text,
        watermark_opacity,
        watermark_size,
        watermark_angle
    }).eq('id', currentStudioId);
    document.getElementById('settings-spinner').classList.add('hidden');
    
    if (error) {
        alert("Ayarlar güncellenemedi: " + error.message);
    } else {
        currentStudioSettings = { 
            ...currentStudioSettings, 
            primary_color, logo_url, watermark_text, 
            watermark_opacity, watermark_size, watermark_angle 
        };
        toggleSettingsModal(false);
        alert("Ayarlar kaydedildi.");
    }
}

// QR Code Logic
window.showQRCode = function() {
    if(!currentEvent) return;
    const url = guestLinkInput.value;
    const container = document.getElementById('qrcode-container');
    container.innerHTML = ''; 
    
    qrCodeObj = new QRCode(container, {
        text: url,
        width: 200,
        height: 200,
        colorDark : "#1a1c1c",
        colorLight : "#ffffff",
        correctLevel : QRCode.CorrectLevel.H
    });
    
    document.getElementById('qr-modal').classList.remove('hidden');
}

window.downloadQRCode = function() {
    const canvas = document.querySelector('#qrcode-container canvas');
    if(!canvas) return;
    const url = canvas.toDataURL("image/png");
    const a = document.createElement('a');
    a.href = url;
    a.download = `QR_${currentEvent.title}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

// Global Tab Switch Logic
window.switchTab = function(tabName) {
    const tabs = ['dashboard', 'events', 'orders', 'feedbacks'];
    
    tabs.forEach(tab => {
        const btn = document.getElementById(`tab-${tab}`);
        if(btn) {
            btn.className = "flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[#f3f3f4] text-[#696868] font-medium transition-colors";
        }
    });
    
    const activeBtn = document.getElementById(`tab-${tabName}`);
    if(activeBtn) {
        activeBtn.className = "flex items-center gap-3 px-3 py-2 rounded-lg bg-[#f0e0c8] text-[#685d4a] font-medium transition-colors";
    }

    document.getElementById('dashboard-details').classList.add('hidden');
    document.getElementById('empty-state').classList.add('hidden');
    document.getElementById('event-details').classList.add('hidden');
    document.getElementById('orders-details').classList.add('hidden');
    document.getElementById('feedbacks-details').classList.add('hidden');
    document.getElementById('sidebar-events-section').classList.add('hidden');

    if(tabName === 'dashboard') {
        document.getElementById('dashboard-details').classList.remove('hidden');
        fetchDashboardStats();
    } else if(tabName === 'events') {
        document.getElementById('sidebar-events-section').classList.remove('hidden');
        if(currentEvent) {
            document.getElementById('event-details').classList.remove('hidden');
        } else {
            document.getElementById('empty-state').classList.remove('hidden');
        }
    } else if(tabName === 'orders') {
        document.getElementById('orders-details').classList.remove('hidden');
        fetchOrders();
    } else if(tabName === 'feedbacks') {
        document.getElementById('feedbacks-details').classList.remove('hidden');
        fetchFeedbacks();
    }
}

// Dashboard Logic
async function fetchDashboardStats() {
    if (!currentStudioId) return;
    let totalRevenue = 0;
    let activeEventsCount = 0;
    let pendingOrdersCount = 0;
    
    const { data: events } = await supabaseClient.from('events').select('id, status').eq('studio_id', currentStudioId);
    if (!events || events.length === 0) {
        document.getElementById('dash-total-revenue').textContent = '0 TL';
        document.getElementById('dash-active-events').textContent = '0';
        document.getElementById('dash-pending-orders').textContent = '0';
        document.getElementById('dash-recent-orders').innerHTML = '<p class="text-sm text-[#696868]">Henüz sipariş yok.</p>';
        document.getElementById('notification-dot').classList.add('hidden');
        return;
    }
    
    activeEventsCount = events.filter(e => e.status === 'active' || !e.status).length;
    const eventIds = events.map(e => e.id);
    
    const { data: orders } = await supabaseClient.from('orders').select('*').in('event_id', eventIds).order('created_at', { ascending: false });
    
    if (orders) {
        totalRevenue = orders.filter(o => o.status === 'completed').reduce((sum, o) => sum + parseFloat(o.total_price || 0), 0);
        pendingOrdersCount = orders.filter(o => o.status === 'pending').length;
        
        // Render recent 5 orders
        const recentContainer = document.getElementById('dash-recent-orders');
        const recentOrders = orders.slice(0, 5);
        if (recentOrders.length > 0) {
            recentContainer.innerHTML = recentOrders.map(o => `
                <div class="flex justify-between items-center py-2 border-b border-[#e2e2e2] last:border-0">
                    <div>
                        <p class="font-bold text-sm">${o.guest_name}</p>
                        <p class="text-xs text-[#696868]">${new Date(o.created_at).toLocaleDateString('tr-TR')}</p>
                    </div>
                    <div class="text-right">
                        <p class="font-bold text-sm">${o.total_price} TL</p>
                        <span class="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${o.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}">${o.status === 'completed' ? 'Tamamlandı' : 'Bekliyor'}</span>
                    </div>
                </div>
            `).join('');
        } else {
            recentContainer.innerHTML = '<p class="text-sm text-[#696868]">Henüz sipariş yok.</p>';
        }
    }

    document.getElementById('dash-total-revenue').textContent = totalRevenue.toLocaleString('tr-TR') + ' TL';
    document.getElementById('dash-active-events').textContent = activeEventsCount;
    document.getElementById('dash-pending-orders').textContent = pendingOrdersCount;
    
    if(pendingOrdersCount > 0) {
        document.getElementById('notification-dot').classList.remove('hidden');
    } else {
        document.getElementById('notification-dot').classList.add('hidden');
    }
}

// Fetch and Render Orders
async function fetchOrders() {
    const container = document.getElementById('orders-list-container');
    container.innerHTML = '<p class="text-sm text-[#696868]">Yükleniyor...</p>';
    
    const { data: events } = await supabaseClient.from('events').select('id, title').eq('studio_id', currentStudioId);
    if(!events || events.length === 0) {
        container.innerHTML = '<p class="text-sm text-[#696868]">Henüz etkinlik bulunmuyor.</p>';
        return;
    }
    const eventIds = events.map(e => e.id);
    const eventMap = {};
    events.forEach(e => eventMap[e.id] = e.title);

    const { data: orders, error } = await supabaseClient.from('orders').select('*').in('event_id', eventIds).order('created_at', { ascending: false });
    
    if(error || !orders || orders.length === 0) {
        container.innerHTML = '<p class="text-sm text-[#696868]">Henüz sipariş bulunmuyor.</p>';
        return;
    }

    let html = '';
    orders.forEach(order => {
        const isCompleted = order.status === 'completed';
        const eventName = eventMap[order.event_id] || "Bilinmeyen Etkinlik";
        const dateStr = new Date(order.created_at).toLocaleString('tr-TR');
        html += `
            <div class="border border-[#e2e2e2] rounded-xl p-4 flex flex-col md:flex-row gap-4 items-start md:items-center justify-between ${isCompleted ? 'bg-[#f9f9f9] opacity-70' : 'bg-white'}">
                <div>
                    <span class="text-xs font-bold px-2 py-1 rounded ${isCompleted ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'} uppercase tracking-wider mb-2 inline-block">
                        ${isCompleted ? 'Tamamlandı' : 'Bekliyor'}
                    </span>
                    <h3 class="font-bold text-[#1a1c1c]">${order.guest_name} <span class="text-sm font-normal text-[#696868]">(${order.guest_contact})</span></h3>
                    <p class="text-sm text-[#4b463d]">Etkinlik: ${eventName} • ${dateStr}</p>
                    <p class="text-sm text-[#685d4a] font-medium mt-1">Seçilen Fotoğraf Sayısı: ${order.photo_ids ? order.photo_ids.length : 0}</p>
                </div>
                <div class="text-right flex flex-col items-end gap-2 shrink-0">
                    <p class="text-xl font-bold text-[#1a1c1c]">${order.total_price > 0 ? order.total_price + ' TL' : 'Ücretsiz'}</p>
                    <div class="flex gap-2">
                        <button onclick="showOrderDetails('${order.id}', '${order.guest_name}')" class="px-3 py-2 bg-white border border-[#cec5ba] text-[#4b463d] rounded-lg text-sm font-medium hover:bg-[#f9f9f9]">Detayları Gör</button>
                        ${!isCompleted ? `<button onclick="completeOrder('${order.id}')" class="px-3 py-2 bg-[#685d4a] text-white rounded-lg text-sm font-medium hover:bg-opacity-90">Tamamlandı</button>` : ''}
                    </div>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

window.completeOrder = async function(orderId) {
    if(!confirm("Siparişi tamamlandı olarak işaretlemek istediğinize emin misiniz?")) return;
    await supabaseClient.from('orders').update({status: 'completed'}).eq('id', orderId);
    fetchOrders(); 
    fetchDashboardStats();
}

// Show Order Details Modal
window.showOrderDetails = async function(orderId, guestName) {
    const modal = document.getElementById('order-details-modal');
    document.getElementById('order-detail-guest').textContent = guestName;
    const grid = document.getElementById('order-photos-grid');
    const loader = document.getElementById('order-photos-loading');
    
    grid.innerHTML = '';
    loader.classList.remove('hidden');
    document.getElementById('order-photo-count').textContent = '...';
    
    modal.classList.remove('hidden');

    const { data: order } = await supabaseClient.from('orders').select('photo_ids').eq('id', orderId).single();
    if (!order || !order.photo_ids || order.photo_ids.length === 0) {
        loader.classList.add('hidden');
        grid.innerHTML = '<p class="col-span-full text-sm text-[#696868]">Fotoğraf bulunamadı.</p>';
        document.getElementById('order-photo-count').textContent = '0';
        return;
    }

    const { data: photos } = await supabaseClient.from('photos').select('id, thumbnail_url, image_url').in('id', order.photo_ids);
    
    loader.classList.add('hidden');
    
    if (photos) {
        document.getElementById('order-photo-count').textContent = photos.length;
        photos.forEach(photo => {
            const div = document.createElement('div');
            div.className = 'aspect-square rounded-lg overflow-hidden border border-[#e2e2e2] cursor-pointer hover:opacity-90 transition-opacity';
            div.onclick = () => window.open(photo.image_url, '_blank');
            div.innerHTML = `<img src="${photo.thumbnail_url || photo.image_url}" class="w-full h-full object-cover">`;
            grid.appendChild(div);
        });
    }
}


// Fetch and Render Feedbacks
async function fetchFeedbacks() {
    const container = document.getElementById('feedbacks-list-container');
    container.innerHTML = '<p class="text-sm text-[#696868]">Yükleniyor...</p>';
    
    const { data: events } = await supabaseClient.from('events').select('id, title').eq('studio_id', currentStudioId);
    if(!events || events.length === 0) return;
    const eventIds = events.map(e => e.id);
    const eventMap = {};
    events.forEach(e => eventMap[e.id] = e.title);

    const { data: photos } = await supabaseClient.from('photos').select('id, event_id, thumbnail_url').in('event_id', eventIds);
    if(!photos || photos.length === 0) return;
    const photoIds = photos.map(p => p.id);
    const photoMap = {};
    photos.forEach(p => photoMap[p.id] = p);

    const { data: feedbacks, error } = await supabaseClient.from('feedbacks').select('*').in('photo_id', photoIds).order('created_at', { ascending: false });
    
    if(error || !feedbacks || feedbacks.length === 0) {
        container.innerHTML = '<p class="text-sm text-[#696868]">Bekleyen geri bildirim (hatalı eşleşme) bulunmuyor.</p>';
        return;
    }

    let html = '';
    feedbacks.forEach(fb => {
        const photo = photoMap[fb.photo_id];
        const eventName = photo ? (eventMap[photo.event_id] || "Bilinmeyen") : "Bilinmeyen";
        const dateStr = new Date(fb.created_at).toLocaleString('tr-TR');
        
        html += `
            <div class="border border-[#e2e2e2] rounded-xl p-4 flex gap-4 items-center bg-white">
                <img src="${photo ? photo.thumbnail_url : ''}" class="w-20 h-20 object-cover rounded-lg bg-[#f3f3f4]">
                <div class="flex-1">
                    <span class="text-xs font-bold px-2 py-1 rounded bg-red-100 text-red-700 uppercase tracking-wider mb-2 inline-block">
                        Hatalı Eşleşme Bildirimi
                    </span>
                    <p class="text-sm text-[#4b463d]">Etkinlik: ${eventName} • ${dateStr}</p>
                </div>
                <div>
                    <button onclick="removeMatch('${fb.face_id}', '${fb.id}')" class="px-4 py-2 bg-red-50 text-red-600 border border-red-200 hover:bg-red-100 rounded-lg text-sm font-medium transition-colors">
                        Eşleşmeyi İptal Et
                    </button>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

window.removeMatch = async function(faceId, feedbackId) {
    if(!confirm("Bu yüzün bu kişiyle (cluster) olan eşleşmesini iptal etmek istediğinize emin misiniz?")) return;
    await supabaseClient.from('faces').update({cluster_id: -1}).eq('id', faceId);
    await supabaseClient.from('feedbacks').delete().eq('id', feedbackId);
    fetchFeedbacks(); 
}

// Start app
init();
