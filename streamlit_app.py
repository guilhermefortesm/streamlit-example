# Importe as bibliotecas necessárias
import googlemaps
import qrcode
from PIL import Image, ImageTk
import tkinter as tk
import random
import string
import easygui
import math
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import sys
import os
import datetime
import csv

# Função para calcular a distância entre dois pontos de latitude e longitude
def calcular_distancia(coord1, coord2):
    lat1, lng1 = coord1
    lat2, lng2 = coord2

    # Cálculo aproximado da distância entre dois pontos geográficos usando a fórmula de Haversine
    R = 6371  # Raio médio da Terra em quilômetros
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(
        dlng / 2) * math.sin(dlng / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distancia = R * c

    return distancia

# Função para criar uma rota ideal com os endereços digitados pelo usuário
def criar_rota(enderecos):
    # Configurar a chave da API do Google Maps
    gmaps = googlemaps.Client(key='AIzaSyDr6dMd09nVkqPxWho8_TmU4EXfeymZdNU')

    # Criar uma lista vazia para armazenar as coordenadas dos endereços
    coordenadas = []

    # Fazer a busca dos endereços no Google Maps e obter as coordenadas
    for endereco in enderecos:
        # Fazer a busca do endereço no Google Maps
        geocode_result = gmaps.geocode(endereco)

        # Verificar se a busca retornou algum resultado
        if geocode_result:
            # Obter as coordenadas do endereço
            lat = geocode_result[0]['geometry']['location']['lat']
            lng = geocode_result[0]['geometry']['location']['lng']

            # Adicionar as coordenadas à lista
            coordenadas.append((lat, lng))
        else:
            print('Endereço não encontrado:', endereco)

    # Inserir o primeiro endereço fixo
    coordenadas.insert(0, (-20.4631, -45.4322))  # Coordenadas de "Rua Jovino Mendes, 2"

    # Criar uma matriz de distâncias entre os endereços
    matriz_distancias = []
    for i in range(len(coordenadas)):
        linha = []
        for j in range(len(coordenadas)):
            if i == j:
                linha.append(0)
            else:
                distancia = calcular_distancia(coordenadas[i], coordenadas[j])
                linha.append(distancia)
        matriz_distancias.append(linha)

    # Resolver o Problema do Caixeiro Viajante usando o algoritmo do Google OR-Tools
    def resolver_tsp(matriz_distancias):
        def criar_data_model(matriz_distancias):
            data = {}
            data['distance_matrix'] = matriz_distancias
            data['num_vehicles'] = 1
            data['depot'] = 0
            return data

        def imprimir_rota(manager, routing, solution):
            print('Distância total: {} km'.format(solution.ObjectiveValue()))
            index = routing.Start(0)
            rota = []
            while not routing.IsEnd(index):
                rota.append(manager.IndexToNode(index))
                index = solution.Value(routing.NextVar(index))
            rota_enderecos = [enderecos[i] for i in rota if i < len(enderecos)]  # Ignorar índices inválidos
            print('Rota:', ' -> '.join(rota_enderecos))

        data = criar_data_model(matriz_distancias)

        # Criação do gerenciador, do roteador e do solucionador
        manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']), data['num_vehicles'], data['depot'])
        routing = pywrapcp.RoutingModel(manager)

        # Configuração do parâmetro de pesquisa
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

        # Configuração das restrições de distância
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data['distance_matrix'][from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Resolve o problema do caixeiro viajante
        solution = routing.SolveWithParameters(search_parameters)

        # Obtém a ordem dos endereços na rota
        index = routing.Start(0)
        rota = []
        while not routing.IsEnd(index):
            rota.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))

        # Reordena a lista de endereços com base na rota otimizada
        rota_enderecos = [enderecos[i] for i in rota if i < len(enderecos)]  # Ignorar índices inválidos
        enderecos_ordenados = []
        for i in range(len(rota_enderecos)):
            enderecos_ordenados.append(rota_enderecos[i])

        # Imprime a rota otimizada
        print('Rota:', ' -> '.join(enderecos_ordenados))

        return enderecos_ordenados

    # Resolver o problema do caixeiro viajante para obter a rota otimizada
    rota_otimizada = resolver_tsp(matriz_distancias)

    # Criar uma string com os endereços na ordem otimizada
    waypoints = '|'.join([f'{endereco}' for endereco in rota_otimizada])

    # Gerar o link da rota otimizada no Google Maps
    route_url = f'https://www.google.com/maps/dir/?api=1&waypoints={waypoints}&travelmode=driving&optimize=true'

    # Criar a pasta para salvar os códigos QR, se ainda não existir
    nome_pasta = "QrCodes"
    if not os.path.exists(nome_pasta):
        os.makedirs(nome_pasta)

    # Obter a data e o horário atual
    data_hora_atual = datetime.datetime.now()
    nome_arquivo = data_hora_atual.strftime('%Y-%m-%d_%H-%M-%S')

    # Gerar o QRCode com o link da rota
    qr = qrcode.QRCode()
    qr.add_data(route_url)
    qr.make()

    # Salvar o QRCode como imagem PNG na pasta
    qr_image_pil = qr.make_image(fill_color="black", back_color="white")
    qr_image_pil.save(os.path.join(nome_pasta, f'{nome_arquivo}.png'))

    # Salvar os dados das rotas
    salvar_dados_rota(rota_otimizada)

    # Criar uma janela separada para exibir o QRCode
    window = tk.Toplevel()
    window.title('QRCode')

    # Carregar a imagem do QRCode
    qr_image = Image.open(os.path.join(nome_pasta, f'{nome_arquivo}.png'))

    # Converter a imagem PIL para o formato Tkinter
    qr_image_tk = ImageTk.PhotoImage(qr_image)

    # Criar um rótulo para exibir o QRCode
    qr_label = tk.Label(window, image=qr_image_tk)
    qr_label.pack()

    # Adicionar um botão de impressão
    def imprimir_qr_code():
        qr_image_pil.show()

    # Criar um botão para imprimir o QR Code
    imprimir_button = tk.Button(window, text="Ok", command=imprimir_qr_code)
    imprimir_button.pack(side=tk.LEFT)

    # Criar um botão para encerrar a janela
    def fechar_janela():
        window.destroy()

    # Criar um botão para encerrar a janela
    fechar_button = tk.Button(window, text="Pronto", command=fechar_janela)
    fechar_button.pack(side=tk.RIGHT)

    # Manter a janela aberta até ser fechada pelo usuário
    window.mainloop()

# Função para ler os endereços digitados pelo usuário
def ler_enderecos():
    enderecos = []

    while True:
        endereco = easygui.enterbox('Digite o endereço (ou pressione Cancel para gerar rota):', 'Endereço')

        if endereco is not None:
            enderecos.append(endereco)
        else:
            break

    return enderecos

# Função para salvar os dados das rotas
def salvar_dados_rota(enderecos_ordenados):
    # Obter a data e o horário atual
    data_hora_atual = datetime.datetime.now()
    nome_pasta = "Historico"

    # Criar a pasta para salvar os dados das rotas, se ainda não existir
    if not os.path.exists(nome_pasta):
        os.makedirs(nome_pasta)

    # Gerar o nome do arquivo com base na data e horário atual
    nome_arquivo = data_hora_atual.strftime('%Y-%m-%d_%H-%M-%S')

    # Criar o arquivo CSV para salvar os dados das rotas na pasta Historico
    with open(os.path.join(nome_pasta, f'{nome_arquivo}.csv'), 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Endereço'])

        for endereco in enderecos_ordenados:
            writer.writerow([endereco])

    print('Dados das rotas salvos com sucesso!')

# Função principal
def main():
    while True:
        # Ler os endereços digitados pelo usuário
        enderecos = ler_enderecos()

        # Criar a rota ideal com os endereços e exibir o QRCode em uma janela separada
        criar_rota(enderecos)

        # Perguntar ao usuário se ele deseja criar uma nova rota
        resposta = easygui.ynbox('Deseja criar uma nova rota?', 'Nova Rota')

        if not resposta:
            break

# Executar a função principal
if __name__ == '__main__':
    main()
