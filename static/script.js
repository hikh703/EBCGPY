document.getElementById("uploadForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const fileInput = document.getElementById("file");
    const userNumberInput = document.getElementById("userNumber");
    const file = fileInput.files[0];
    const userNumber = userNumberInput.value;

    if (!file || !userNumber) {
        alert("Please upload a file and enter a user number.");
        return;
    }



    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("user_number", userNumberInput.value);
    
    try {
        const response = await fetch("http://127.0.0.1:8000/generate-labels", {
            method: "POST",
            body: formData,
        });
    
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
    
            const downloadLink = document.getElementById("downloadLink");
            downloadLink.href = url;
            document.getElementById("downloadLinkContainer").style.display = "block";
        } else {
            console.error("Failed to generate labels:", response.statusText);
        }
    } catch (error) {
        console.error("Error:", error);
    }
    
});
