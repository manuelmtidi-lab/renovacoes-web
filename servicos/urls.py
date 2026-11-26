from django.urls import path

from . import crud

urlpatterns = [
    path("clientes/", crud.cliente_lista, name="cliente_lista"),
    path("clientes/novo/", crud.cliente_novo, name="cliente_novo"),
    path("clientes/<int:pk>/", crud.cliente_detalhe, name="cliente_detalhe"),
    path("clientes/<int:pk>/editar/", crud.cliente_editar, name="cliente_editar"),
    path("clientes/<int:pk>/apagar/", crud.cliente_apagar, name="cliente_apagar"),
    path("projectos/", crud.projecto_lista, name="projecto_lista"),
    path("projectos/novo/", crud.projecto_novo, name="projecto_novo"),
    path("projectos/<int:pk>/", crud.projecto_detalhe, name="projecto_detalhe"),
    path("projectos/<int:pk>/editar/", crud.projecto_editar, name="projecto_editar"),
    path("projectos/<int:pk>/apagar/", crud.projecto_apagar, name="projecto_apagar"),
    path("servicos/", crud.servico_lista, name="servico_lista"),
    path("servicos/exportar/", crud.servico_exportar, name="servico_exportar"),
    path("servicos/novo/", crud.servico_novo, name="servico_novo"),
    path("servicos/<int:pk>/", crud.servico_detalhe, name="servico_detalhe"),
    path("servicos/<int:pk>/editar/", crud.servico_editar, name="servico_editar"),
    path("servicos/<int:pk>/renovar/", crud.servico_renovar, name="servico_renovar"),
    path("actividade/", crud.actividade, name="actividade"),
    path("servicos/<int:pk>/proforma/", crud.servico_proforma, name="servico_proforma"),
    path("servicos/<int:pk>/tratamento/", crud.servico_tratamento, name="servico_tratamento"),
    path("servicos/<int:pk>/apagar/", crud.servico_apagar, name="servico_apagar"),
]
