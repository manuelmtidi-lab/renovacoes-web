# Painel de renovações

Painel web para controlar domínios, hosting, certificados SSL, manutenções e licenças dos clientes de uma empresa de desenvolvimento: o que expira, quando, quanto custa e quem está a tratar da renovação.

Projecto de estágio (Tunganetu / Instituto Técnico Comercial de Luanda). **Todos os dados de exemplo são inventados.**

## Funcionalidades

- Clientes, projectos e serviços, com pesquisa, filtros, paginação e exportação para CSV.
- Painel com serviços em atraso, a expirar em 7 e 30 dias, receita prevista, margem e gráfico dos últimos 12 meses.
- Calendário das expirações.
- Registo de renovações (individual e em lote), com a nova data calculada pelo ciclo do serviço (mensal a bienal).
- Estados de tratamento (por contactar, contactado, proforma enviada, pago) e notas por serviço.
- Botão "Avisar por WhatsApp" com a mensagem já escrita.
- Proforma em PDF (sem custo nem margem).
- Custo opcional em dólares, com câmbio actualizado por comando.
- Alertas por email (60, 30 e 7 dias) e resumo semanal.
- Histórico de actividade (só Administrador).
- Login por email e palavra-passe ou Google. Não há registo aberto: só entra quem um administrador já criou.
- PWA instalável. As páginas com dados nunca ficam em cache.

## Perfis

| Perfil | Pode |
|---|---|
| Administrador | Tudo, incluindo apagar e ver a Actividade |
| Gestor comercial | Criar e editar, renovar, exportar, proforma, WhatsApp |
| Técnico | Só ver os serviços dos projectos que lhe estão atribuídos |

## Stack

Django 6.1, PostgreSQL 17, django-allauth, HTMX, Tailwind 4 (django-tailwind-cli), Chart.js, ReportLab, Docker Compose.

## Instalação (desenvolvimento)

Precisas de Docker e Docker Compose.

```bash
git clone https://github.com/manuelmtidi-lab/renovacoes-web.git
cd renovacoes-web
cp .env.example .env        # preenche os valores
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py dados_demo   # opcional: dados inventados
```

Abre `http://localhost:8000` (usa sempre `localhost`, por causa do login Google).

**Nunca uses `docker compose down -v`: apaga a base de dados.**

Testes:

```bash
docker compose exec web python manage.py test servicos
```

## Comandos de gestão

| Comando | O que faz | Frequência sugerida |
|---|---|---|
| `enviar_alertas` | Alertas de expiração por email (`--simular` para ver sem enviar) | Diária |
| `resumo_semanal` | Resumo ao Administrador e Gestor (`--simular`) | Segunda de manhã |
| `actualizar_cambio` | Actualiza USD/Kz e recalcula custos (`--manual 920`) | Semanal |
| `verificar_ssl` | Compara a data real do certificado com a registada (`--aplicar` para actualizar) | Semanal |

O câmbio automático vem de uma fonte pública de mercado, não do BNA. Confirma o valor antes de confiar nele.

## Limitações

- Por omissão os emails saem para a consola. Para envio real, configura SMTP no `.env`.
- O histórico de actividade não regista alterações feitas no Django Admin nem pelos comandos.
- `verificar_ssl` lê o certificado instalado no servidor, que pode não ser o contratado. Não há verificação de expiração de domínios.
- O serviço de câmbio e o login Google precisam de internet.
- Ainda não há configuração de produção (Gunicorn, Nginx, HTTPS, `DEBUG=False`). Está planeada.

## Privacidade

Guarda-se apenas o contacto dos clientes (Lei n.º 22/11, Protecção de Dados Pessoais, Angola). Não se guardam palavras-passe de painéis de hosting ou registadores. Nunca faças commit do `.env` nem de dados reais.
