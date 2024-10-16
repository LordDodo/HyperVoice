# client.py

import sys
import socket
import threading
import pyaudio
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QLineEdit, QLabel, QInputDialog,
    QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject

# Paramètres audio
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class AudioStream(QObject):
    error = pyqtSignal(str)

    def __init__(self, device_index=None):
        super().__init__()
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.device_index = device_index

    def start_stream(self):
        try:
            self.stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                output=True,
                frames_per_buffer=CHUNK,
                output_device_index=self.device_index
            )
        except OSError as e:
            self.error.emit(f"Erreur audio: {str(e)}")

    def stop_stream(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()

    def __del__(self):
        self.stop_stream()

class Client(QObject):
    received_users = pyqtSignal(list)
    received_rooms = pyqtSignal(list)
    received_all_users = pyqtSignal(list)
    connection_error = pyqtSignal(str)

    def __init__(self, host, port_controle, port_audio):
        super().__init__()
        self.host = host
        self.port_controle = port_controle
        self.port_audio = port_audio
        self.socket_controle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_audio = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.audio_stream = None
        self.current_room = None
        self.connected = False
        self.audio_connected = False

    def connect_to_server(self, pseudo, device_index=None):
        try:
            # Connexion au serveur de contrôle
            self.socket_controle.connect((self.host, self.port_controle))
            self.connected = True

            # Attendre le prompt "USERNAME"
            prompt = self.socket_controle.recv(1024).decode()
            if prompt == "USERNAME":
                self.send_control_data(pseudo)

            # Envoyer le pseudo au serveur audio
            self.socket_audio.connect((self.host, self.port_audio))
            self.socket_audio.send(pseudo.encode())
            self.audio_connected = True

            # Initialiser le flux audio
            self.audio_stream = AudioStream(device_index)
            self.audio_stream.error.connect(self.handle_audio_error)
            self.audio_stream.start_stream()

            # Lancer les threads de réception
            threading.Thread(target=self.receive_control_data, daemon=True).start()
            threading.Thread(target=self.receive_audio_data, daemon=True).start()

            return True
        except Exception as e:
            self.connection_error.emit(f"Erreur de connexion: {str(e)}")
            return False

    def send_control_data(self, data):
        if not self.connected:
            return
        try:
            self.socket_controle.send(data.encode())
        except Exception as e:
            self.connection_error.emit(f"Erreur d'envoi: {str(e)}")
            self.connected = False

    def receive_control_data(self):
        while self.connected:
            try:
                data = self.socket_controle.recv(1024).decode()
                if not data:
                    break
                if data.startswith("USERS:"):
                    users = data[6:].split(',')
                    self.received_users.emit(users)
                elif data.startswith("ALL_USERS:"):
                    all_users = data[10:].split(',')
                    self.received_all_users.emit(all_users)
                elif data.startswith("ROOMS:"):
                    rooms = data[6:].split(',')
                    self.received_rooms.emit(rooms)
                else:
                    pass  # Messages non reconnus
            except Exception as e:
                self.connection_error.emit(f"Erreur de réception: {str(e)}")
                self.connected = False
                break

    def receive_audio_data(self):
        while self.audio_connected:
            try:
                data = self.socket_audio.recv(CHUNK)
                if not data:
                    break
                if data.startswith(b"USERS:"):
                    users = data[6:].decode().split(',')
                    self.received_users.emit(users)
                elif data.startswith(b"ROOMS:"):
                    rooms = data[6:].decode().split(',')
                    self.received_rooms.emit(rooms)
                else:
                    if self.audio_stream and self.audio_stream.stream:
                        self.audio_stream.stream.write(data)
            except Exception as e:
                self.connection_error.emit(f"Erreur audio: {str(e)}")
                self.audio_connected = False
                break

    def join_room(self, room_name):
        if self.current_room:
            self.leave_room()
        self.send_control_data(f"JOIN:{room_name}")
        self.current_room = room_name
        threading.Thread(target=self.send_audio, daemon=True).start()

    def send_audio(self):
        while self.current_room and self.connected and self.audio_stream:
            try:
                data = self.audio_stream.stream.read(CHUNK, exception_on_overflow=False)
                self.socket_audio.send(data)
            except Exception as e:
                self.connection_error.emit(f"Erreur d'envoi audio: {str(e)}")
                break

    def leave_room(self):
        if self.current_room:
            self.send_control_data(f"LEAVE:{self.current_room}")
            self.current_room = None

    def create_room(self, room_name):
        if room_name:
            self.send_control_data(f"CREATE:{room_name}")

    def handle_audio_error(self, error_message):
        self.connection_error.emit(error_message)

    def get_all_users(self):
        self.send_control_data("GET_USERS")

    def get_all_rooms(self):
        self.send_control_data("GET_ROOMS")

    def close_connections(self):
        self.leave_room()
        if self.socket_controle:
            try:
                self.socket_controle.close()
            except:
                pass
        if self.socket_audio:
            try:
                self.socket_audio.close()
            except:
                pass
        if self.audio_stream:
            self.audio_stream.stop_stream()

class FenetrePrincipale(QMainWindow):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.client.received_users.connect(self.mettre_a_jour_utilisateurs)
        self.client.received_rooms.connect(self.mettre_a_jour_salons)
        self.client.received_all_users.connect(self.mettre_a_jour_tous_utilisateurs)
        self.client.connection_error.connect(self.afficher_erreur)
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Chat Vocal")
        self.setStyleSheet("background-color: #36393F; color: white;")

        central_widget = QWidget()
        main_layout = QHBoxLayout()

        # Panneau de gauche pour la liste des salons
        panneau_gauche = QWidget()
        layout_gauche = QVBoxLayout()

        label_salons = QLabel("Salons Vocaux")
        label_salons.setStyleSheet("font-weight: bold; font-size: 18px;")
        layout_gauche.addWidget(label_salons)

        self.liste_salons = QListWidget()
        self.liste_salons.setStyleSheet("background-color: #2C2F33; color: white; border-radius: 5px;")
        self.liste_salons.itemDoubleClicked.connect(self.rejoindre_salon)
        layout_gauche.addWidget(self.liste_salons)

        entree_nouveau_salon = QLineEdit()
        entree_nouveau_salon.setPlaceholderText("Nouveau salon...")
        entree_nouveau_salon.setStyleSheet("background-color: #40444B; color: white; border-radius: 5px; padding: 5px;")
        layout_gauche.addWidget(entree_nouveau_salon)

        bouton_creer_salon = QPushButton("Créer un salon")
        bouton_creer_salon.setStyleSheet("""
            QPushButton {
                background-color: #43B581;
                color: white;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #3CA374;
            }
        """)
        bouton_creer_salon.clicked.connect(lambda: self.creer_salon(entree_nouveau_salon.text()))
        layout_gauche.addWidget(bouton_creer_salon)

        panneau_gauche.setLayout(layout_gauche)
        main_layout.addWidget(panneau_gauche)

        # Panneau de droite pour la liste des utilisateurs
        panneau_droit = QWidget()
        layout_droit = QVBoxLayout()

        label_utilisateurs = QLabel("Utilisateurs Connectés")
        label_utilisateurs.setStyleSheet("font-weight: bold; font-size: 18px;")
        layout_droit.addWidget(label_utilisateurs)

        self.liste_utilisateurs = QListWidget()
        self.liste_utilisateurs.setStyleSheet("background-color: #2C2F33; color: white; border-radius: 5px;")
        layout_droit.addWidget(self.liste_utilisateurs)

        bouton_quitter_salon = QPushButton("Quitter le salon")
        bouton_quitter_salon.setStyleSheet("""
            QPushButton {
                background-color: #F04747;
                color: white;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #D84040;
            }
        """)
        bouton_quitter_salon.clicked.connect(self.quitter_salon)
        layout_droit.addWidget(bouton_quitter_salon)

        panneau_droit.setLayout(layout_droit)
        main_layout.addWidget(panneau_droit)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.setGeometry(100, 100, 800, 600)

    def creer_salon(self, nom_salon):
        if nom_salon:
            self.client.create_room(nom_salon)

    def rejoindre_salon(self, item):
        salon = item.text()
        self.client.join_room(salon)

    def quitter_salon(self):
        self.client.leave_room()
        self.liste_utilisateurs.clear()

    def mettre_a_jour_utilisateurs(self, utilisateurs):
        self.liste_utilisateurs.clear()
        self.liste_utilisateurs.addItems(utilisateurs)

    def mettre_a_jour_salons(self, salons):
        self.liste_salons.clear()
        if salons != ['']:
            self.liste_salons.addItems(salons)

    def mettre_a_jour_tous_utilisateurs(self, tous_utilisateurs):
        # Afficher tous les utilisateurs connectés, même sans salon
        self.liste_utilisateurs.clear()
        self.liste_utilisateurs.addItems(tous_utilisateurs)

    def afficher_erreur(self, message):
        QMessageBox.critical(self, "Erreur", message)

def selectionner_peripherique_sortie():
    p = pyaudio.PyAudio()
    liste_peripheriques = []
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info["maxOutputChannels"] > 0:
            liste_peripheriques.append((i, info["name"]))
    p.terminate()

    if not liste_peripheriques:
        QMessageBox.critical(None, "Erreur Audio", "Aucun périphérique de sortie audio disponible.")
        sys.exit()

    # Créer une fenêtre de sélection
    app = QApplication(sys.argv)
    dialog = QMessageBox()
    dialog.setWindowTitle("Sélection du périphérique de sortie")
    dialog.setText("Aucun périphérique de sortie par défaut. Veuillez sélectionner un périphérique :")
    
    # Ajouter un combo box pour la sélection
    combo = QComboBox()
    for index, nom in liste_peripheriques:
        combo.addItem(nom, index)
    dialog.layout().addWidget(combo, 1, 1)

    dialog.addButton(QMessageBox.StandardButton.Ok)
    dialog.exec()

    if dialog.clickedButton() == dialog.buttons()[0]:
        return combo.currentData()
    else:
        sys.exit()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "serveur":
        print("Veuillez exécuter 'serveur.py' pour lancer le serveur.")
    else:
        app = QApplication(sys.argv)
        client = Client("localhost", 12345, 12346)

        # Sélection du périphérique de sortie audio
        p = pyaudio.PyAudio()
        output_device_index = None
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info["maxOutputChannels"] > 0:
                output_device_index = i
                break
        p.terminate()

        if output_device_index is None:
            # Aucun périphérique de sortie par défaut trouvé, demander à l'utilisateur de sélectionner
            output_device_index = selectionner_peripherique_sortie()

        # Connexion au serveur
        pseudo, ok = QInputDialog.getText(None, "Pseudo", "Entrez votre pseudo :")
        if ok and pseudo:
            if client.connect_to_server(pseudo, output_device_index):
                # Récupérer la liste des utilisateurs et salons
                client.get_all_users()
                client.get_all_rooms()

                fenetre = FenetrePrincipale(client)
                fenetre.show()
                sys.exit(app.exec())
            else:
                QMessageBox.critical(None, "Erreur", "Impossible de se connecter au serveur.")
        else:
            QMessageBox.critical(None, "Erreur", "Pseudo non fourni.")
