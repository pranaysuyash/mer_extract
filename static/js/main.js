Dropzone.autoDiscover = false;

document.addEventListener('DOMContentLoaded', function() {
    const myDropzone = new Dropzone("#my-dropzone", {
        url: "/upload",
        acceptedFiles: "application/pdf,image/*",
        addRemoveLinks: true,
        maxFilesize: 30, // MB
    });

    const resultsDiv = document.getElementById('results');
    
    myDropzone.on("success", function(file, response) {
        if (response.error) {
            console.error("Server error:", response.error);
            const resultItem = document.createElement('div');
            resultItem.className = 'result-item error';
            resultItem.innerHTML = `
                <p>File: ${file.name}</p>
                <p>Status: Error</p>
                <p>Message: ${response.error}</p>
            `;
            resultsDiv.appendChild(resultItem);
        } else {
            const resultItem = document.createElement('div');
            resultItem.className = 'result-item';
            resultItem.innerHTML = `
                <p>File: ${file.name}</p>
                <p>Status: Success</p>
                <a href="/download/${response.filename}" download>Download CSV</a>
            `;
            resultsDiv.appendChild(resultItem);
        }
    });

    myDropzone.on("error", function(file, errorMessage, xhr) {
        console.error("Upload error:", errorMessage);
        const resultItem = document.createElement('div');
        resultItem.className = 'result-item error';
        resultItem.innerHTML = `
            <p>File: ${file.name}</p>
            <p>Status: Error</p>
            <p>Message: ${errorMessage}</p>
        `;
        resultsDiv.appendChild(resultItem);
    });
});
