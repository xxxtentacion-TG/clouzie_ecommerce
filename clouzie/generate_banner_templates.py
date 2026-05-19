import os

list_html = """{% extends 'adminpanel/base.html' %}
{% block title %}Banners — CLOUZIE{% endblock %}
{% block content %}
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600;700&family=Barlow+Condensed:wght@500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--black:#0a0a0a;--white:#fff;--grey-50:#fafafa;--grey-100:#f5f5f5;--grey-200:#ebebeb;--grey-300:#d4d4d4;--grey-400:#a3a3a3;--grey-500:#737373;--grey-600:#525252;--green-bg:#d1fae5;--green-fg:#065f46;--green-dot:#059669;--red-bg:#fee2e2;--red-fg:#b91c1c;--red-dot:#dc2626;--font-display:'Barlow Condensed',sans-serif;--font-body:'Barlow',sans-serif;--radius-sm:6px;--radius-md:10px;--radius-lg:14px;--shadow-sm:0 1px 3px rgba(0,0,0,.06);--shadow-md:0 4px 16px rgba(0,0,0,.08);--shadow-lg:0 20px 48px rgba(0,0,0,.12)}
body{font-family:var(--font-body)}
.adm{background:var(--white);min-height:100vh;padding:48px 56px 80px;color:var(--black)}
.adm-header{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:40px;gap:20px;flex-wrap:wrap;opacity:0;animation:fadeUp .55s .02s cubic-bezier(.22,1,.36,1) forwards}
.adm-eyebrow{font-family:var(--font-display);font-size:10px;font-weight:600;letter-spacing:.22em;text-transform:uppercase;color:var(--grey-400);margin-bottom:6px}
.adm-title{font-family:var(--font-display);font-size:44px;font-weight:700;letter-spacing:-.01em;line-height:1;color:var(--black);text-transform:uppercase}
.adm-header-right{display:flex;align-items:center;gap:12px}
.adm-btn-primary{display:inline-flex;align-items:center;gap:8px;padding:12px 22px;background:var(--black);color:var(--white);font-family:var(--font-display);font-size:12px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;border-radius:var(--radius-md);border:none;cursor:pointer;white-space:nowrap;transition:background .18s,transform .15s,box-shadow .18s;text-decoration:none}
.adm-btn-primary:hover{background:#222;transform:translateY(-1px);box-shadow:0 6px 18px rgba(0,0,0,.2)}
.adm-btn-primary svg{width:16px;height:16px}
.adm-table-card{border:1.5px solid var(--grey-200);border-radius:var(--radius-lg);overflow:hidden;box-shadow:var(--shadow-sm);opacity:0;animation:fadeUp .55s .18s cubic-bezier(.22,1,.36,1) forwards}
.adm-table-toolbar{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;border-bottom:1px solid var(--grey-200);background:var(--grey-50)}
.adm-table-toolbar-title{font-family:var(--font-display);font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--grey-500)}
.adm-table-count{font-family:var(--font-display);font-size:11px;font-weight:600;letter-spacing:.08em;color:var(--grey-400);background:var(--grey-200);padding:3px 10px;border-radius:100px}
.adm-table-scroll{width:100%;overflow-x:auto}
.adm-table{width:100%;border-collapse:collapse}
.adm-table thead tr{background:var(--grey-50);border-bottom:1.5px solid var(--grey-200)}
.adm-table thead th{font-family:var(--font-display);padding:13px 16px;font-size:9.5px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--grey-400);text-align:left;white-space:nowrap}
.adm-table thead th.align-right{text-align:right;padding-right:20px}
.adm-table tbody tr{border-bottom:1px solid var(--grey-200);transition:background .12s;opacity:0;animation:rowSlide .4s cubic-bezier(.22,1,.36,1) forwards}
.adm-table tbody tr:hover{background:var(--grey-50)}
.adm-table tbody td{padding:15px 16px;vertical-align:middle;font-size:13px;color:var(--black)}
.adm-badge{display:inline-flex;align-items:center;gap:5px;padding:4px 11px;border-radius:100px;font-family:var(--font-display);font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;white-space:nowrap}
.adm-badge-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0}
.adm-badge.active{background:var(--green-bg);color:var(--green-fg)}.adm-badge.active .adm-badge-dot{background:var(--green-dot)}
.adm-badge.inactive{background:var(--red-bg);color:var(--red-fg)}.adm-badge.inactive .adm-badge-dot{background:var(--red-dot)}
.adm-action-td{text-align:right;padding-right:16px;white-space:nowrap}
.adm-btn-action{display:inline-flex;align-items:center;justify-content:center;width:32px;height:32px;border-radius:var(--radius-sm);color:var(--grey-500);background:transparent;border:1px solid transparent;transition:all .18s;cursor:pointer;margin-left:4px}
.adm-btn-action:hover{background:var(--grey-100);color:var(--black);border-color:var(--grey-200)}
.adm-btn-action.delete:hover{background:var(--red-bg);color:var(--red-fg);border-color:#fca5a5}
.adm-btn-action svg{width:14px;height:14px}
.adm-empty{text-align:center;padding:60px 24px;color:var(--grey-400)}
.adm-empty svg{width:40px;height:40px;margin:0 auto 12px;display:block;opacity:.4}
.adm-empty p{font-size:13px}
/* toggle */
.offer-toggle{position:relative;display:inline-block;width:40px;height:22px}
.offer-toggle input{opacity:0;width:0;height:0}
.offer-slider{position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background:var(--grey-300);transition:.3s;border-radius:22px}
.offer-slider:before{position:absolute;content:"";height:16px;width:16px;left:3px;bottom:3px;background:#fff;transition:.3s;border-radius:50%;box-shadow:0 1px 3px rgba(0,0,0,.15)}
input:checked+.offer-slider{background:var(--black)}
input:checked+.offer-slider:before{transform:translateX(18px)}
/* delete modal */
.adm-modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.45);backdrop-filter:blur(4px);z-index:9999;display:none;align-items:center;justify-content:center;padding:20px}
.adm-modal-overlay.open{display:flex}
.adm-modal{background:var(--white);border-radius:var(--radius-lg);width:100%;max-width:420px;box-shadow:var(--shadow-lg);overflow:hidden;animation:modalPop .25s ease}
@keyframes modalPop{from{transform:scale(.95) translateY(12px);opacity:0}to{transform:scale(1) translateY(0);opacity:1}}
.delete-modal-body{padding:40px 32px 28px;text-align:center}
.delete-icon-wrap{width:60px;height:60px;background:var(--red-bg);border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 20px}
.delete-icon-wrap svg{width:28px;height:28px;color:var(--red-fg)}
.delete-modal-title{font-family:var(--font-display);font-size:20px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;margin-bottom:10px}
.delete-modal-desc{font-size:13.5px;color:var(--grey-500);line-height:1.6;max-width:280px;margin:0 auto 28px}
.delete-modal-actions{display:flex;justify-content:center;gap:10px}
.adm-btn-secondary{padding:10px 18px;font-family:var(--font-display);font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;border-radius:var(--radius-sm);background:var(--white);border:1.5px solid var(--grey-300);color:var(--grey-600);cursor:pointer;transition:all .18s}
.adm-btn-secondary:hover{border-color:var(--grey-500);color:var(--black)}
.adm-btn-submit{padding:10px 22px;font-family:var(--font-display);font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;border-radius:var(--radius-sm);background:var(--black);border:1.5px solid var(--black);color:var(--white);cursor:pointer;transition:all .18s}
.adm-btn-submit:hover{background:#333;border-color:#333}
.adm-btn-danger{background:#dc2626;border-color:#dc2626}
.adm-btn-danger:hover{background:#b91c1c;border-color:#b91c1c}
/* toast */
.cl-toast{position:fixed;top:32px;right:32px;z-index:10000;display:flex;align-items:flex-start;gap:14px;background:rgba(255,255,255,.95);backdrop-filter:blur(12px);border:1px solid var(--grey-200);border-radius:var(--radius-md);padding:16px 20px;width:320px;box-shadow:0 20px 40px rgba(0,0,0,.08);transform:translateX(120%);opacity:0;transition:transform .4s cubic-bezier(.22,1,.36,1),opacity .4s;pointer-events:none}
.cl-toast.show{transform:translateX(0);opacity:1;pointer-events:auto}
.cl-toast-icon{width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.cl-toast-icon.success{background:var(--green-bg);color:var(--green-fg)}
.cl-toast-icon.error{background:var(--red-bg);color:var(--red-fg)}
.cl-toast-icon svg{width:14px;height:14px}
.cl-toast-content{flex:1}
.cl-toast-title{font-family:var(--font-display);font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--black);margin-bottom:4px}
.cl-toast-message{font-size:12.5px;color:var(--grey-500);line-height:1.4}
.adm-discount{font-family:var(--font-display);font-size:15px;font-weight:700;color:var(--black);letter-spacing:.02em}
.adm-date{font-size:12.5px;color:var(--grey-600);white-space:nowrap}
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
@keyframes rowSlide{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
@media(max-width:900px){.adm{padding:28px 20px 60px}.adm-title{font-size:34px}}
@media(max-width:640px){.adm{padding:20px 14px 60px}.adm-header{flex-direction:column;align-items:flex-start;gap:14px}}
</style>

<div class="adm">
  <!-- HEADER -->
  <div class="adm-header">
    <div>
      <div class="adm-eyebrow">Admin Panel</div>
      <h1 class="adm-title">Banners</h1>
    </div>
    <div class="adm-header-right">
      <a href="{% url 'adminpanel:create_banner' %}" class="adm-btn-primary">
        <svg fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        Add Banner
      </a>
    </div>
  </div>

  <!-- TABLE -->
  <div class="adm-table-card">
    <div class="adm-table-toolbar">
      <span class="adm-table-toolbar-title">All Banners</span>
      <span class="adm-table-count" id="rowCount">{{ banners|length }} total</span>
    </div>
    <div class="adm-table-scroll">
      <table class="adm-table" id="bannerTable">
        <thead>
          <tr>
            <th>Image</th>
            <th>Title</th>
            <th>Placement</th>
            <th>Validity</th>
            <th>Status</th>
            <th>Toggle</th>
            <th class="align-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {% for banner in banners %}
          <tr id="banner-row-{{ banner.id }}">
            <td>
                {% if banner.image %}
                <img src="{{ banner.image.url }}" alt="Banner" style="width: 80px; height: 40px; object-fit: cover; border-radius: 4px;">
                {% endif %}
            </td>
            <td style="font-weight:600">{{ banner.title }}</td>
            <td><span style="font-family:var(--font-display);font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;background:var(--grey-100);border:1px solid var(--grey-200);padding:3px 9px;border-radius:var(--radius-sm);color:var(--grey-600)">{{ banner.get_placement_display }}</span></td>
            <td><span class="adm-date">
                {% if banner.start_date %}{{ banner.start_date|date:"M d, Y" }}{% else %}Anytime{% endif %} → 
                {% if banner.end_date %}{{ banner.end_date|date:"M d, Y" }}{% else %}Anytime{% endif %}
            </span></td>
            <td>
              <span class="adm-badge {% if banner.is_active %}active{% else %}inactive{% endif %}" id="badge-{{ banner.id }}">
                <span class="adm-badge-dot"></span>
                {% if banner.is_active %}Active{% else %}Inactive{% endif %}
              </span>
            </td>
            <td>
              <label class="offer-toggle" title="Toggle banner">
                <input type="checkbox" {% if banner.is_active %}checked{% endif %}
                       onchange="toggleBanner({{ banner.id }}, this)">
                <span class="offer-slider"></span>
              </label>
            </td>
            <td class="adm-action-td">
              <a href="{% url 'adminpanel:edit_banner' banner.id %}" class="adm-btn-action" title="Edit">
                <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </a>
              <button class="adm-btn-action delete" title="Delete" onclick="openDeleteModal({{ banner.id }})">
                <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
              </button>
            </td>
          </tr>
          {% empty %}
          <tr>
            <td colspan="7">
              <div class="adm-empty">
                <svg fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>
                <p>No banners yet. <a href="{% url 'adminpanel:create_banner' %}" style="color:var(--black);font-weight:600">Create one</a>.</p>
              </div>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- DELETE CONFIRM MODAL -->
<div class="adm-modal-overlay" id="deleteModal">
  <div class="adm-modal">
    <div class="delete-modal-body">
      <div class="delete-icon-wrap">
        <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>
      </div>
      <div class="delete-modal-title">Delete Banner?</div>
      <p class="delete-modal-desc">This action will remove the banner permanently. It cannot be undone.</p>
      <div class="delete-modal-actions">
        <button class="adm-btn-secondary" onclick="closeDeleteModal()">Cancel</button>
        <button class="adm-btn-submit adm-btn-danger" id="confirmDeleteBtn" onclick="confirmDelete()">Delete</button>
      </div>
    </div>
  </div>
</div>

<!-- TOAST -->
<div class="cl-toast" id="clToast">
  <div class="cl-toast-icon" id="clToastIcon">
    <svg fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" id="clToastSvg"><polyline points="20 6 9 17 4 12"/></svg>
  </div>
  <div class="cl-toast-content">
    <div class="cl-toast-title" id="clToastTitle">Success</div>
    <div class="cl-toast-message" id="clToastMsg"></div>
  </div>
</div>

<script>
const CSRF = '{{ csrf_token }}';
let deleteTargetId = null;

function getCsrf(){ return CSRF; }

function showToast(msg, success=true){
  const t=document.getElementById('clToast');
  const icon=document.getElementById('clToastIcon');
  const title=document.getElementById('clToastTitle');
  const msgEl=document.getElementById('clToastMsg');
  const svg=document.getElementById('clToastSvg');
  icon.className='cl-toast-icon '+(success?'success':'error');
  title.textContent=success?'Success':'Error';
  msgEl.textContent=msg;
  svg.innerHTML=success?'<polyline points="20 6 9 17 4 12"/>':'<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>';
  t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),3500);
}

function openDeleteModal(id){
  deleteTargetId=id;
  document.getElementById('deleteModal').classList.add('open');
}
function closeDeleteModal(){
  deleteTargetId=null;
  document.getElementById('deleteModal').classList.remove('open');
}
document.getElementById('deleteModal').addEventListener('click', e=>{ if(e.target===e.currentTarget) closeDeleteModal(); });

function confirmDelete(){
  if(!deleteTargetId) return;
  const btn=document.getElementById('confirmDeleteBtn');
  btn.disabled=true; btn.textContent='Deleting…';
  fetch(`/adminpanel/banners/${deleteTargetId}/delete/`,{
    method:'POST', headers:{'X-CSRFToken':getCsrf(),'Content-Type':'application/json'}
  }).then(r=>r.json()).then(data=>{
    closeDeleteModal();
    if(data.success){
      const row=document.getElementById('banner-row-'+deleteTargetId);
      if(row){ row.style.transition='opacity .3s'; row.style.opacity='0'; setTimeout(()=>row.remove(),300); }
      showToast(data.message, true);
    } else { showToast('Could not delete banner.', false); }
    btn.disabled=false; btn.textContent='Delete';
  }).catch(()=>{ showToast('Network error.', false); btn.disabled=false; btn.textContent='Delete'; });
}

function toggleBanner(id, checkbox){
  checkbox.disabled=true;
  fetch(`/adminpanel/banners/${id}/toggle/`,{
    method:'POST', headers:{'X-CSRFToken':getCsrf(),'Content-Type':'application/json'}
  }).then(r=>r.json()).then(data=>{
    checkbox.disabled=false;
    if(data.success){
      checkbox.checked=data.is_active;
      const badge=document.getElementById('badge-'+id);
      if(badge){
        badge.className='adm-badge '+(data.is_active?'active':'inactive');
        badge.innerHTML=`<span class="adm-badge-dot"></span>${data.is_active?'Active':'Inactive'}`;
      }
      showToast(data.message, true);
    } else { checkbox.checked=!checkbox.checked; showToast('Toggle failed.', false); }
  }).catch(()=>{ checkbox.disabled=false; checkbox.checked=!checkbox.checked; showToast('Network error.', false); });
}

document.addEventListener('keydown', e=>{ if(e.key==='Escape') closeDeleteModal(); });
</script>
{% endblock %}"""

form_html = """{% extends 'adminpanel/base.html' %}
{% block title %}{{ action }} Banner — CLOUZIE{% endblock %}
{% block content %}
<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@300;400;500;600;700&family=Barlow+Condensed:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root{--black:#0a0a0a;--white:#fff;--grey-100:#f5f5f5;--grey-200:#ebebeb;--grey-300:#d4d4d4;--grey-400:#a3a3a3;--grey-500:#737373;--grey-600:#525252;--font-display:'Barlow Condensed',sans-serif;--font-body:'Barlow',sans-serif;--radius-md:10px;--radius-lg:14px;--shadow-sm:0 1px 3px rgba(0,0,0,.06)}
body{font-family:var(--font-body)}
.adm{background:var(--white);min-height:100vh;padding:48px 56px 80px;color:var(--black)}
.adm-header{margin-bottom:40px;opacity:0;animation:fadeUp .5s cubic-bezier(.22,1,.36,1) forwards}
.adm-eyebrow{font-family:var(--font-display);font-size:10px;font-weight:600;letter-spacing:.22em;text-transform:uppercase;color:var(--grey-400);margin-bottom:6px}
.adm-title{font-family:var(--font-display);font-size:44px;font-weight:700;letter-spacing:-.01em;line-height:1;color:var(--black);text-transform:uppercase}
.adm-card{border:1.5px solid var(--grey-200);border-radius:var(--radius-lg);padding:32px;box-shadow:var(--shadow-sm);opacity:0;animation:fadeUp .5s .1s cubic-bezier(.22,1,.36,1) forwards;max-width:800px}
.form-group{margin-bottom:24px}
.form-label{display:block;font-family:var(--font-display);font-size:12px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--grey-500);margin-bottom:8px}
.form-control{width:100%;border:1.5px solid var(--grey-300);border-radius:var(--radius-md);padding:14px 16px;font-family:var(--font-body);font-size:14px;color:var(--black);outline:none;transition:border-color .2s,box-shadow .2s;background:#fff}
.form-control:focus{border-color:var(--black);box-shadow:0 0 0 3px rgba(0,0,0,.05)}
.form-control::placeholder{color:var(--grey-400)}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.adm-btn-submit{padding:14px 28px;font-family:var(--font-display);font-size:13px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;border-radius:var(--radius-md);background:var(--black);border:1.5px solid var(--black);color:var(--white);cursor:pointer;transition:all .2s;margin-top:10px}
.adm-btn-submit:hover{background:#333;border-color:#333;transform:translateY(-1px);box-shadow:0 6px 18px rgba(0,0,0,.15)}
.img-preview{margin-top:12px;border:1.5px solid var(--grey-200);border-radius:var(--radius-md);overflow:hidden;background:var(--grey-100);display:flex;align-items:center;justify-content:center;height:200px}
.img-preview img{width:100%;height:100%;object-fit:cover;display:none}
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
</style>

<div class="adm">
  <div class="adm-header">
    <div class="adm-eyebrow"><a href="{% url 'adminpanel:banner_list' %}" style="color:var(--grey-500);text-decoration:none;margin-right:8px">← Back to Banners</a></div>
    <h1 class="adm-title">{{ action }} Banner</h1>
  </div>

  <div class="adm-card">
    <form method="POST" enctype="multipart/form-data">
      {% csrf_token %}
      
      <div class="form-group">
        <label class="form-label">Banner Title</label>
        <input type="text" name="title" class="form-control" placeholder="e.g. Summer Collection 2026" value="{{ banner.title|default:'' }}" required>
      </div>

      <div class="form-group">
        <label class="form-label">Subtitle / Description</label>
        <textarea name="subtitle" class="form-control" rows="3" placeholder="Enter banner subtitle">{{ banner.subtitle|default:'' }}</textarea>
      </div>

      <div class="form-group">
        <label class="form-label">Banner Image (Desktop & Mobile)</label>
        <input type="file" name="image" class="form-control" accept="image/*" id="bannerImg" {% if not banner %}required{% endif %}>
        <div class="img-preview" id="imgPreviewContainer">
          {% if banner and banner.image %}
          <img src="{{ banner.image.url }}" alt="Preview" id="imgPreview" style="display:block">
          {% else %}
          <img src="#" alt="Preview" id="imgPreview">
          <span style="font-family:var(--font-display);color:var(--grey-400);font-size:14px;letter-spacing:0.1em;text-transform:uppercase" id="imgPlaceholder">Image Preview</span>
          {% endif %}
        </div>
      </div>

      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Button Text</label>
          <input type="text" name="button_text" class="form-control" placeholder="e.g. SHOP NOW" value="{{ banner.button_text|default:'' }}">
        </div>
        <div class="form-group">
          <label class="form-label">Button Link</label>
          <input type="text" name="button_link" class="form-control" placeholder="e.g. /category/summer" value="{{ banner.button_link|default:'' }}">
        </div>
      </div>

      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Start Date</label>
          <input type="date" name="start_date" class="form-control" value="{{ start_date|default:'' }}">
        </div>
        <div class="form-group">
          <label class="form-label">End Date</label>
          <input type="date" name="end_date" class="form-control" value="{{ end_date|default:'' }}">
        </div>
      </div>

      <button type="submit" class="adm-btn-submit">{{ action }} Banner</button>
    </form>
  </div>
</div>

<script>
document.getElementById('bannerImg').addEventListener('change', function(e){
  const file = e.target.files[0];
  if(file){
    const reader = new FileReader();
    reader.onload = function(e){
      const img = document.getElementById('imgPreview');
      img.src = e.target.result;
      img.style.display = 'block';
      const ph = document.getElementById('imgPlaceholder');
      if(ph) ph.style.display = 'none';
    }
    reader.readAsDataURL(file);
  }
});
</script>
{% endblock %}"""

os.makedirs(r'f:\brototype\clouzie\clouzie\adminpanel\templates\adminpanel\banners', exist_ok=True)
with open(r'f:\brototype\clouzie\clouzie\adminpanel\templates\adminpanel\banners\banner_list.html', 'w', encoding='utf-8') as f:
    f.write(list_html)

with open(r'f:\brototype\clouzie\clouzie\adminpanel\templates\adminpanel\banners\banner_form.html', 'w', encoding='utf-8') as f:
    f.write(form_html)
