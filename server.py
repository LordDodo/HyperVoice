# serveur.py

import socket
import threading
import sys
import time

class Serveur:
    def __init__(self, hote, port_controle, port_audio):
        self.hote = hote
        self.port_controle = port_controle
        self.port_audio = port_audio
        self.socket_controle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_audio = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients_controle = {}  # client_socket: {"pseudo": str, "salon": str}
        self.salons = {}  # salon: set(client_socket)

    def demarrer(self):
        # Démarrer le serveur de contrôle
        self.socket_controle.bind((self.hote, self.port_controle))
        self.socket_controle.listen(5)
        print(f"Serveur de contrôle en écoute sur {self.hote}:{self.port_controle}")

        # Démarrer le serveur audio
        self.socket_audio.bind((self.hote, self.port_audio))
        self.socket_audio.listen(5)
        print(f"Serveur audio en écoute sur {self.hote}:{self.port_audio}")

        # Thread pour accepter les connexions de contrôle
        threading.Thread(target=self.accepter_connexions_controle, daemon=True).start()
        # Thread pour accepter les connexions audio
        threading.Thread(target=self.accepter_connexions_audio, daemon=True).start()

        # Garder le serveur en marche
        while True:
            time.sleep(1)

    def accepter_connexions_controle(self):
        while True:
            client_socket, adresse = self.socket_controle.accept()
            print(f"Nouvelle connexion de contrôle de {adresse}")
            threading.Thread(target=self.gerer_client_controle, args=(client_socket,), daemon=True).start()

    def accepter_connexions_audio(self):
        while True:
            client_audio_socket, adresse = self.socket_audio.accept()
            print(f"Nouvelle connexion audio de {adresse}")
            threading.Thread(target=self.gerer_client_audio, args=(client_audio_socket,), daemon=True).start()

    def gerer_client_controle(self, client_socket):
        try:
            # Demander le pseudo
            client_socket.send("USERNAME".encode())
            pseudo = client_socket.recv(1024).decode().strip()
            if not pseudo:
                client_socket.close()
                return
            self.clients_controle[client_socket] = {"pseudo": pseudo, "salon": None}
            print(f"Pseudo '{pseudo}' enregistré.")

            # Envoyer la liste actuelle des salons
            self.envoyer_salons(client_socket)

            # Envoyer la liste des utilisateurs connectés
            self.envoyer_utilisateurs()

            # Écouter les messages de contrôle
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                self.process_message_controle(client_socket, data)
        except Exception as e:
            print(f"Erreur avec le client de contrôle: {e}")
        finally:
            self.supprimer_client_controle(client_socket)

    def gerer_client_audio(self, client_audio_socket):
        try:
            # Recevoir l'identifiant du client audio (pseudo)
            pseudo = client_audio_socket.recv(1024).decode().strip()
            if not pseudo:
                client_audio_socket.close()
                return

            # Trouver le socket de contrôle correspondant
            client_controle = None
            for cs, info in self.clients_controle.items():
                if info["pseudo"] == pseudo:
                    client_controle = cs
                    break

            if not client_controle:
                client_audio_socket.close()
                return

            # Associer le socket audio au client de contrôle
            self.clients_controle[client_controle]["audio"] = client_audio_socket
            print(f"Connexion audio établie pour '{pseudo}'.")

            # Écouter les données audio et les diffuser
            while True:
                data = client_audio_socket.recv(1024)
                if not data:
                    break
                self.diffuser_audio(client_controle, data)
        except Exception as e:
            print(f"Erreur avec le client audio: {e}")
        finally:
            self.supprimer_client_audio(client_audio_socket)

    def process_message_controle(self, client_socket, message):
        try:
            message = message.decode().strip()
            if message.startswith("CREATE:"):
                salon = message[7:]
                self.creer_salon(salon)
            elif message.startswith("JOIN:"):
                salon = message[5:]
                self.rejoindre_salon(client_socket, salon)
            elif message.startswith("LEAVE:"):
                salon = message[6:]
                self.quitter_salon(client_socket, salon)
            elif message == "GET_USERS":
                self.envoyer_utilisateurs()
            elif message == "GET_ROOMS":
                self.envoyer_salons(client_socket)
            else:
                pass  # Messages non reconnus
        except Exception as e:
            print(f"Erreur en traitant le message de contrôle: {e}")

    def creer_salon(self, salon):
        if salon not in self.salons:
            self.salons[salon] = set()
            print(f"Salon '{salon}' créé.")
            self.broadcast_salons()
        else:
            print(f"Le salon '{salon}' existe déjà.")

    def rejoindre_salon(self, client_socket, salon):
        if salon not in self.salons:
            self.creer_salon(salon)
        # Quitter l'ancien salon
        ancien_salon = self.clients_controle[client_socket]["salon"]
        if ancien_salon:
            self.salons[ancien_salon].remove(client_socket)
            self.diffuser_salon(ancien_salon, f"{self.clients_controle[client_socket]['pseudo']} a quitté le salon.")
        # Rejoindre le nouveau salon
        self.salons[salon].add(client_socket)
        self.clients_controle[client_socket]["salon"] = salon
        print(f"{self.clients_controle[client_socket]['pseudo']} a rejoint le salon '{salon}'.")
        self.diffuser_salon(salon, f"{self.clients_controle[client_socket]['pseudo']} a rejoint le salon.")
        self.envoyer_utilisateurs_salons(salon)

    def quitter_salon(self, client_socket, salon):
        if salon in self.salons and client_socket in self.salons[salon]:
            self.salons[salon].remove(client_socket)
            self.clients_controle[client_socket]["salon"] = None
            print(f"{self.clients_controle[client_socket]['pseudo']} a quitté le salon '{salon}'.")
            self.diffuser_salon(salon, f"{self.clients_controle[client_socket]['pseudo']} a quitté le salon.")
            self.envoyer_utilisateurs_salons(salon)

    def diffuser_audio(self, client_socket, data):
        salon = self.clients_controle[client_socket]["salon"]
        if salon and salon in self.salons:
            for client in self.salons[salon]:
                if client != client_socket and "audio" in self.clients_controle[client]:
                    try:
                        self.clients_controle[client]["audio"].send(data)
                    except:
                        self.supprimer_client_controle(client)

    def envoyer_utilisateurs_salons(self, salon):
        if salon not in self.salons:
            return
        utilisateurs = [info["pseudo"] for cs, info in self.clients_controle.items() if info["salon"] == salon]
        message = "USERS:" + ",".join(utilisateurs)
        for client in self.salons[salon]:
            try:
                self.clients_controle[client]["audio"].send(message.encode())
            except:
                self.supprimer_client_controle(client)

    def envoyer_utilisateurs(self):
        utilisateurs = [info["pseudo"] for info in self.clients_controle.values()]
        message = "ALL_USERS:" + ",".join(utilisateurs)
        for client in self.clients_controle:
            try:
                client.send(message.encode())
            except:
                self.supprimer_client_controle(client)

    def envoyer_salons(self, client_socket=None):
        salons = list(self.salons.keys())
        message = "ROOMS:" + ",".join(salons)
        if client_socket:
            try:
                client_socket.send(message.encode())
            except:
                self.supprimer_client_controle(client_socket)
        else:
            for client in self.clients_controle:
                try:
                    client.send(message.encode())
                except:
                    self.supprimer_client_controle(client)

    def broadcast_salons(self):
        self.envoyer_salons()

    def diffuser_salon(self, salon, message):
        if salon not in self.salons:
            return
        for client in self.salons[salon]:
            try:
                client.send(message.encode())
            except:
                self.supprimer_client_controle(client)

    def supprimer_client_controle(self, client_socket):
        if client_socket in self.clients_controle:
            salon = self.clients_controle[client_socket]["salon"]
            pseudo = self.clients_controle[client_socket]["pseudo"]
            if salon and salon in self.salons:
                self.salons[salon].remove(client_socket)
                self.diffuser_salon(salon, f"{pseudo} s'est déconnecté.")
                self.envoyer_utilisateurs_salons(salon)
            print(f"Déconnexion de {pseudo}.")
            del self.clients_controle[client_socket]
            self.envoyer_utilisateurs()
            self.envoyer_salons(client_socket)
        try:
            client_socket.close()
        except:
            pass

    def supprimer_client_audio(self, client_audio_socket):
        # Trouver le client de contrôle associé
        client_controle = None
        for cs, info in self.clients_controle.items():
            if "audio" in info and info["audio"] == client_audio_socket:
                client_controle = cs
                break
        if client_controle:
            self.clients_controle[client_controle].pop("audio", None)
            salon = self.clients_controle[client_controle]["salon"]
            if salon:
                self.diffuser_salon(salon, f"{self.clients_controle[client_controle]['pseudo']} a perdu la connexion audio.")
                self.envoyer_utilisateurs_salons(salon)
        try:
            client_audio_socket.close()
        except:
            pass

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "serveur":
        serveur = Serveur("localhost", 12345, 12346)
        serveur.demarrer()
    else:
        print("Usage: python serveur.py serveur")
