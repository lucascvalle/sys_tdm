# SysOrc

Este é o repositório para o sistema de gerenciamento de orçamentos `SysOrc`.

## Descrição do Projeto

O `SysOrc` é um sistema desenvolvido para gerenciar o ciclo completo de orçamentos. Ele permite a criação, edição e exportação de orçamentos para o formato Excel, focando na gestão eficiente dos itens de orçamento e seus cálculos.

## Funcionalidades

- Criação e edição de orçamentos com adição/remoção dinâmica de itens.
- Cálculos automáticos de valores por item e total do orçamento.
- Persistência e edição de orçamentos e seus itens.
- Geração de documentos de orçamento para arquivos Excel (`.xlsx`).
- Estilização da interface do usuário com as cores da marca.
- Integração com o painel administrativo do Django para gerenciamento de templates de produtos.

## Configuração do Ambiente

Este projeto utiliza Docker para facilitar a configuração do ambiente de desenvolvimento.

1.  **Pré-requisitos:**
    *   Docker Desktop (ou Docker Engine e Docker Compose) instalado.

2.  **Clonar o Repositório:**
    ```bash
    git clone https://github.com/lucascvalle/sys_tdm.git
    cd sys_tdm
    ```

3.  **Construir e Iniciar os Contêineres:**
    ```bash
    docker-compose up --build
    ```

4.  **Executar Migrações (Primeira Vez):**
    Após os contêineres estarem rodando, você precisará executar as migrações do Django para configurar o banco de dados:
    ```bash
    docker-compose exec web python sys_tdm/manage.py migrate
    ```

5.  **Criar Superusuário (Opcional, para acesso ao Admin):**
    ```bash
    docker-compose exec web python sys_tdm/manage.py createsuperuser
    ```

## Uso

Após a configuração, o sistema estará acessível em `http://localhost:8000` (ou a porta configurada no seu `docker-compose.yml`).

- **Acessar o Admin:** `http://localhost:8000/admin`
- **Listar Orçamentos:** `http://localhost:8000/orcamentos/`
- **Exportar Orçamento:** Na página de edição de um orçamento, haverá um botão para exportar para Excel.

## Contribuição

Sinta-se à vontade para contribuir com o projeto. Por favor, siga as boas práticas de Git e abra Pull Requests para novas funcionalidades ou correções de bugs.