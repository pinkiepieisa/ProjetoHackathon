# app_backend.py
from flask import Flask, request, jsonify
from flask_cors import CORS 
import speech_recognition as sr
import io
import time

app = Flask(__name__)
CORS(app) 

r = sr.Recognizer()

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    audio_data = request.data
    
    if not audio_data:
        return jsonify({"success": False, "transcription": "Nenhum dado de áudio recebido."}), 400

    try:
        # O MediaRecorder no Frontend está enviando um Blob WebM com codec PCM (áudio não compactado).
        # Para que o SpeechRecognition do Python consiga lidar com formatos mais complexos,
        # vamos usar o .recognize_google, que é mais tolerante ao receber o formato Blob WebM (MIME type: audio/webm).
        
        # O objeto AudioFile de SpeechRecognition lida melhor com arquivos ou streams.
        # Vamos tratar o buffer como um arquivo (File-like object) para o Google entender o WebM.
        
        # Cria um objeto de arquivo temporário na memória a partir dos bytes.
        audio_file = io.BytesIO(audio_data)
        
        # Tenta carregar o áudio (o Google consegue processar o WebM diretamente)
        with sr.AudioFile(audio_file) as source:
            audio_segment = r.record(source) 

        # Transcreve usando o motor do Google (online)
        transcription = r.recognize_google(audio_segment, language="pt-BR")
        
        time.sleep(0.1) 
        
        return jsonify({
            "success": True, 
            "transcription": transcription
        })

    except sr.UnknownValueError:
        # Silêncio ou áudio ininteligível
        return jsonify({"success": False, "transcription": ""}), 200 # Retornamos string vazia para limpar a legenda
    except sr.RequestError as e:
        # Problemas de rede
        return jsonify({"success": False, "transcription": f"Erro de Serviço: {e}"}), 500
    except Exception as e:
        # Outros erros
        return jsonify({"success": False, "transcription": f"Erro Interno: {e}"}), 500


if __name__ == '__main__':
    app.run(port=5001, debug=False)