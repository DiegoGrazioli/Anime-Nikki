function validateLoginForm() {
    var username = document.getElementById("username").value;
    var password = document.getElementById("password").value;

    if (username === "" || password === "") {
        alert("Entrambi i campi username e password devono essere compilati.");
        return false;
    }
    document.getElementById("loginbutton").onclick(() => 
        document.getElementById("form").submit()
    );
}