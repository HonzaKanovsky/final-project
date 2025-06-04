from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def client_home():
    return render_template_string('''
        <h1>Client Interface</h1>
        <video id="video" autoplay playsinline width="320" height="240"></video>
        <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
        <script>
        const video = document.getElementById('video');
        const canvas = document.createElement('canvas');
        let streaming = false;
        let socket = io('http://165.246.116.218:5001'); // TODO: Replace with actual admin server IP

        navigator.mediaDevices.getUserMedia({ video: true, audio: false })
          .then(stream => {
            video.srcObject = stream;
            video.play();
            streaming = true;
            sendFrames();
          });

        function sendFrames() {
          if (!streaming) return;
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          canvas.getContext('2d').drawImage(video, 0, 0);
          canvas.toBlob(blob => {
            if (blob) {
              const reader = new FileReader();
              reader.onload = function() {
                socket.emit('video_frame', { frame: reader.result });
              };
              reader.readAsDataURL(blob);
            }
            setTimeout(sendFrames, 50); // ~20 FPS
          }, 'image/jpeg', 0.7);
        }
        </script>
    ''')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True) 