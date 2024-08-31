

document.getElementById('toggle-btn').addEventListener('click', function() {
    const navMenu = document.getElementById('menubar');
    navMenu.classList.toggle('show');
});

// dropZone setting
let dropZone = document.getElementById('drop_zone');

dropZone.addEventListener('dragover', function(e) {
    e.preventDefault();
    dropZone.style.border = '2px dashed #333';
});

dropZone.addEventListener('dragleave', function(e) {
    e.preventDefault();
    dropZone.style.border = '10px dashed #ccc';
});

dropZone.addEventListener('drop', function(e) {
    e.preventDefault();
    dropZone.style.border = '10px dashed #ccc';
    if (e.dataTransfer.files.length > 0) {
        console.log("addEventLister_drop!",e.dataTransfer.files);
		document.getElementById('userfile').files = e.dataTransfer.files;
		document.getElementById('userfile').dispatchEvent(new Event('change'));
	}
});

document.getElementById('userfile').addEventListener('change', function(e) {
    // 2回目以降のアップロード時
    document.getElementById('complete-container').style.display = 'none'; // 完了メッセージを非表示
    document.getElementById('file-name').textContent = "No file chosen";

    const file = e.target.files[0];
    const errorMessage = document.getElementById('error-message');
    const fileName = e.target.files.length > 0 ? file.name : 'No file chosen';
    const fileType = file.type;
    const uploadButton = document.getElementById('uploadButton');
    document.getElementById('file-name').textContent = fileName;
    // MP4ファイルのみ許可
    if (fileType !== 'video/mp4') {
        errorMessage.textContent = 'Error: Only MP4 files are allowed.';
        errorMessage.style.display = 'inline'; // エラーメッセージを表示
        e.target.value = ''; // 選択されたファイルをクリア
        if (uploadButton.disabled == false){
            uploadButton.disabled = true;
            uploadButton.classList.add('disabled-button');
            uploadButton.classList.remove('orange-button');
        }
    } else {
        errorMessage.style.display = 'none'; // エラーメッセージを非表示
        uploadButton.disabled = false;
        uploadButton.classList.remove('disabled-button');
        uploadButton.classList.add('orange-button');
    }
});

// fileBox setting

// let userfile = document.getElementById('userfile');
// userfile.addEventListener('change', function(e) {
//     let file = document.getElementById('fileBox');
//     console.log(file.value);
//     if (e.dataTransfer.files.length > 0) {
// 		document.getElementById('userfile').files = e.dataTransfer.files;
// 		document.getElementById('userfile').dispatchEvent(new Event('change'));
// 	}
// });

// upload button setting
let uploadButton = document.getElementById('uploadButton');
uploadButton.addEventListener('click', function(e) {
    uploadButton.disabled = true;
    document.getElementById('userfile').disabled = true;
    uploadFile(document.getElementById('userfile').files[0]);
});

// function
async function uploadFile(file) {
    let formData = new FormData();
    formData.append('file', file);
    console.log('Uploading...!');

    try {
        let response = await fetch('/synthesia2midi/upload', {
            method: 'POST',
            body: formData
        });

        let data = await response.json(); 
        console.log('Upload successful:', data.file_name);

        await pollProgress();

        // Show download link or further processing results
    
        createDownload(data);
        
    } catch (error) {
        console.error('Error:', error);
    }
}

async function pollProgress() {
    return new Promise((resolve)=>{
    const progressBar = document.getElementById('progress-bar');
    const progressContainer = document.getElementById('progress-container');
    progressContainer.style.display = 'block';

    const intervalId = setInterval(function() {
        fetch('/synthesia2midi/progress')
            .then(response => response.json())
            .then(data => {
                const percentComplete = data.progress;
                if (!Number.isNaN(Number(percentComplete))) {
                    progressBar.style.width = percentComplete + '%';
                    
                    if (percentComplete >= 100) {
                        clearInterval(intervalId);
                        progressContainer.style.display = 'none';
                        resolve();
                    }
                }
            })
            .catch(error => console.error('Error fetching progress:', error));
    }, 1000); // Poll every second
    });
}

function createDownload(data) {
    // 処理後のファイル名を取得
    const fileNameWithoutExt = data.file_name.replace(/\.[^/.]+$/, "");
    const downloadUrl = "processed/" + fileNameWithoutExt + ".midi";
    console.log('download_filename:', downloadUrl);
    // ダウンロードボタンの表示と設定
    document.getElementById('complete-container').style.display = 'block';
    
    // 再びアップロードを許可
    document.getElementById('userfile').disabled = false;
    document.getElementById('userfile').value = ''; // ファイル入力をリセット

    document.getElementById('downloadButton').addEventListener('click', function() {
        fetch("/synthesia2midi/download",{
            method: 'POST',
            headers: {
                'Content-Type': 'application/json' // JSON データを送信することを指定
            },
            body: JSON.stringify({
                filename: downloadUrl
            })
        })
        .then(response => response.blob())
        .then(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = fileNameWithoutExt + ".midi";
            document.body.appendChild(a);
            a.click();
            URL.revokeObjectURL(url);

        })
        .catch(error => console.error('Error:', error));
    });
}
