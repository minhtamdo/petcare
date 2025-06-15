document.addEventListener("DOMContentLoaded", () => {
    const user = {
        name: "jdoe",
        fullname: "John Doe",
        email: "jdoe@example.com",
        phone: "0123456789",
        created: "2024-12-01"
    };

    document.getElementById("name").value = user.name;
    document.getElementById("fullname").value = user.fullname;
    document.getElementById("email").value = user.email;
    document.getElementById("phone").value = user.phone;
    document.getElementById("created").value = user.created;

    const editBtn = document.getElementById("edit-btn");
    let isEditing = false;

    editBtn.addEventListener("click", () => {
        isEditing = !isEditing;
        document.querySelectorAll("input").forEach(input => {
            input.readOnly = !isEditing;
            input.style.backgroundColor = isEditing ? "#ffffff" : "#f9f9f9";
        });
        editBtn.textContent = isEditing ? "Lưu" : "Chỉnh sửa";

        if (!isEditing) {
            alert("Thông tin đã được cập nhật!");
        }
    });

    document.getElementById("logout-btn").addEventListener("click", () => {
    alert("Bạn đã quay lại trang chủ");
    window.location.href = "HomePage.html";
});
});
