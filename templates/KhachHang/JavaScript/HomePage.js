let cart = [];

function addToCart(itemName, price, quantity = 1) {
    const existingItem = cart.find(item => item.name === itemName);
    if (existingItem) {
        existingItem.quantity += quantity;
    } else {
        cart.push({ name: itemName, price: price, quantity: quantity });
    }
    updateCart();
}

function updateCart() {
    const cartItems = document.getElementById('cart-items');
    const cartTotal = document.getElementById('cart-total');
    cartItems.innerHTML = '';
    let total = 0;

    cart.forEach(item => {
        total += item.price * item.quantity;
        const div = document.createElement('div');
        div.className = 'cart-item';
        div.innerHTML = `<span>${item.name}</span> <span>${(item.price * item.quantity).toLocaleString()}đ</span> <span>Số Lượng: ${item.quantity}</span> <button onclick="removeOneItem('${item.name}')">Xóa</button>`;
        cartItems.appendChild(div);
    });

    cartTotal.textContent = `Tổng Cộng: ${total.toLocaleString()}đ`;
}

function removeOneItem(itemName) {
    const item = cart.find(item => item.name === itemName);
    if (item) {
        item.quantity -= 1;
        if (item.quantity <= 0) {
            cart = cart.filter(item => item.name !== itemName);
        }
        updateCart();
    }
}

function toggleSubServices(id) {
    const subServices = document.getElementById(id);
    subServices.classList.toggle('active');
}

function toggleResidenceForm() {
    const form = document.getElementById('residence-form');
    form.classList.toggle('active');
}

function generatePetForms() {
    const petCount = document.getElementById('pet-count').value;
    const petForms = document.getElementById('pet-forms');
    petForms.innerHTML = '';
    for (let i = 0; i < petCount; i++) {
        const div = document.createElement('div');
        div.className = 'pet-form';
        div.innerHTML = `<h4>Thông tin thú cưng ${i + 1}</h4><input type="text" placeholder="Tên thú cưng"><textarea placeholder="Ghi chú"></textarea>`;
        petForms.appendChild(div);
    }
}

function bookResidence() {
    alert('Đặt lịch cư trú thành công!');
}

function openBookingModal() {
    document.getElementById('booking-modal').classList.add('active');
}

function closeModal() {
    document.getElementById('booking-modal').classList.remove('active');
}

function confirmBooking() {
    const date = document.getElementById('appointment-date').value;
    const time = document.getElementById('appointment-time').value;
    const petCount = document.getElementById('pet-count-modal').value;
    if (date && time && petCount) {
        document.getElementById('notification').textContent = `Đặt lịch thành công vào ${date} lúc ${time} cho ${petCount} thú cưng!`;
        document.getElementById('notification').classList.add('active');
        setTimeout(() => {
            document.getElementById('notification').classList.remove('active');
        }, 3000);
        closeModal();
    } else {
        alert('Vui lòng điền đầy đủ thông tin!');
    }
}

// Quản lý đăng nhập/đăng xuất
function updateLoginButton() {
    const loginText = document.getElementById('login-text');
    const loginBtn = document.getElementById('login-btn');
    const dropdownMenu = document.getElementById('dropdown-menu');
    const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
    const username = localStorage.getItem('username');

    if (!loginBtn || !loginText || !dropdownMenu) {
        console.error('Không tìm thấy loginBtn, loginText hoặc dropdownMenu');
        return;
    }

    // Xóa sự kiện cũ
    loginBtn.onclick = null;
    loginBtn.removeEventListener('click', handleLogin);
    loginBtn.removeEventListener('click', toggleDropdown);

    if (isLoggedIn && username) {
        loginText.textContent = username;
        loginBtn.addEventListener('click', toggleDropdown);
    } else {
        loginText.textContent = 'Đăng nhập';
        loginBtn.addEventListener('click', handleLogin);
    }
}

function handleLogin() {
    const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
    if (!isLoggedIn) {
        console.log('Chưa đăng nhập, chuyển hướng đến DangNhap.html...');
        window.location.href = "DangNhap.html";
    } else {
        console.log('Đã đăng nhập, không cần chuyển hướng.');
    }
}




function handleLogout() {
    localStorage.setItem('isLoggedIn', 'false');
    localStorage.removeItem('username');
    updateLoginButton();
    const dropdownMenu = document.getElementById('dropdown-menu');
    if (dropdownMenu) {
        dropdownMenu.classList.remove('active');
    }

    alert('Bạn đã đăng xuất thành công!');
}


function toggleDropdown() {
    const dropdownMenu = document.getElementById('dropdown-menu');
    dropdownMenu.classList.toggle('active');
}

document.addEventListener('click', (event) => {
    const dropdownMenu = document.getElementById('dropdown-menu');
    const loginBtn = document.getElementById('login-btn');
    if (!loginBtn.contains(event.target)) {
        dropdownMenu.classList.remove('active');
    }
});

window.onload = () => {
    console.log('Trang đã tải hoàn tất (window.onload), gọi updateLoginButton...');
    updateLoginButton();
};

document.addEventListener('DOMContentLoaded', () => {
    console.log('Trang đã tải hoàn tất (DOMContentLoaded), gọi updateLoginButton...');
    updateLoginButton();
});
// thông tin tìa khoản
document.addEventListener('DOMContentLoaded', () => {
    // Cập nhật nút Thông tin tài khoản để kiểm tra đăng nhập trước khi chuyển trang
    const accountBtn = document.getElementById('account-info-btn');
    if (accountBtn) {
        accountBtn.addEventListener('click', () => {
            const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
            if (isLoggedIn) {
                window.location.href = 'ThongTinTK.html'; 
            } else {
                alert('Bạn chưa đăng nhập!');
                window.location.href = 'DangNhap.html';
            }
        });
    }
});

