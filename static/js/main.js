// post click start
document.querySelectorAll('.post-link').forEach(wrapper => {
    wrapper.style.cursor = 'pointer';
    wrapper.addEventListener('click', () => {
        const href = wrapper.getAttribute('data-href');
        if (href) {
            window.location.href = href;
        }
    });
});
// post click end

// create post button pointer start
document.querySelectorAll('.create-post').forEach(wrapper => {
    wrapper.style.cursor = 'pointer';
});
// create post button pointer end

// fullscreen modal start
document.getElementById('showPostForm')?.addEventListener('click', () => {
    document.getElementById('postModal').style.display = 'block';
});

document.getElementById('closePostForm')?.addEventListener('click', () => {
    document.getElementById('postModal').style.display = 'none';
})

document.addEventListener('DOMContentLoaded', function () {
    const postModal = document.getElementById('postModal');
    if (postModal) {
        postModal.addEventListener('click', function (e) {
            if (e.target === postModal) {
                postModal.style.display = 'none';
            }
        })
    }
})
// fullscreen modal end

// quill tool loading start
document.addEventListener("DOMContentLoaded", function () {
    const editorContainer = document.getElementById("editor-container");
    if (!editorContainer) {
        console.error("missing #editor-container div.");
        return;
    }

    const quill = new Quill("#editor-container", {
        theme: "snow",
        modules: {
            toolbar: "#toolbar"
        }
    });

    const dropdown = document.querySelector('.custom-font-size-dropdown');
    const toggle = dropdown.querySelector('.dropdown-toggle');
    const menu = dropdown.querySelector('.dropdown-menu');
    const options = menu.querySelectorAll('li');

    toggle.addEventListener('click', () => {
        menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
    });

    options.forEach(option => {
        option.addEventListener('click', () => {
            const size = option.getAttribute('data-size');
            quill.format('size', size);
            menu.style.display = 'none';
            toggle.textContent = option.textContent;
        });
    });

    document.addEventListener('click', (e) => {
        if (!dropdown.contains(e.target)) {
            menu.style.display = 'none';
        }
    });

    const form = document.querySelector("form");
    form.addEventListener("submit", function () {
        const hiddenInput = document.querySelector("#hidden-content");
        hiddenInput.value = quill.root.innerHTML;
    });
});
// quill tool loading end

// attachment tools start
document.addEventListener("DOMContentLoaded", function () {
    const fileInput = document.getElementById('attachment-input');
    const previewContainer = document.getElementById('attachment-preview');
    let filesArray = [];

    fileInput.addEventListener('change', function (e) {
        for (const file of Array.from(e.target.files)) {
            if (!filesArray.some(f => f.name === file.name && f.size === file.size)) {
                filesArray.push(file);
            }
        }
        updatePreview();
        fileInput.value = '';
    });

    function updatePreview() {
        previewContainer.innerHTML = '';
        filesArray.forEach((file, idx) => {
            const wrapper = document.createElement('div');
            wrapper.style.display = 'flex';
            wrapper.style.alignItems = 'center';
            wrapper.style.gap = '6px';
            wrapper.style.background = '#071322';
            wrapper.style.border = '2px solid #2a2735';
            wrapper.style.borderRadius = '8px';
            wrapper.style.padding = '6px 10px';

            if (file.type.startsWith('image/')) {
                const img = document.createElement('img');
                img.style.maxWidth = '64px';
                img.style.maxHeight = '64px';
                img.style.borderRadius = '6px';
                img.style.marginRight = '8px';
                img.src = URL.createObjectURL(file);
                img.onload = () => URL.revokeObjectURL(img.src);
                wrapper.appendChild(img);
            }
            else {
                const icon = document.createElement('span');
                icon.textContent = '📄';
                icon.style.fontSize = '1.5em';
                wrapper.appendChild(icon);
            }

            const name = document.createElement('span');
            name.textContent = file.name;
            name.style.marginRight = '8px';
            wrapper.appendChild(name);

            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.textContent = '✖';
            removeBtn.className = 'attachment-remove-btn';
            removeBtn.title = 'Remove';
            removeBtn.onclick = () => {
                filesArray.splice(idx, 1);
                updatePreview();
            };
            wrapper.appendChild(removeBtn);

            previewContainer.appendChild(wrapper);
        });
    }

    const form = document.querySelector("form");
    form.addEventListener("submit", function (e) {
        const dt = new DataTransfer();
        filesArray.forEach(f => dt.items.add(f));
        fileInput.files = dt.files;
    });
});
// attachment tools end

// font swap start
document.addEventListener("DOMContentLoaded", function () {
    const fontToggleBtn = document.getElementById('fontToggleBtn');
    if (localStorage.getItem('readableFont') === 'true') {
        document.body.classList.add('readable-font'); // <-- This line is needed!
        if (fontToggleBtn) fontToggleBtn.textContent = 'Switch to Default Font';
    } else {
        if (fontToggleBtn) fontToggleBtn.textContent = 'Switch Font';
    }

    if (fontToggleBtn) {
        fontToggleBtn.addEventListener('click', function () {
            document.body.classList.toggle('readable-font');
            const isReadable = document.body.classList.contains('readable-font');
            localStorage.setItem('readableFont', isReadable ? 'true' : 'false');
            fontToggleBtn.textContent = isReadable ? 'Switch to Default Font' : 'Switch Font';
        });
    }
});
// font swap end