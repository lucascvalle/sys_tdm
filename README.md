# sys_tdm

Este é o repositório para o sistema de gerenciamento de orçamentos `sys_tdm`.

## Descrição do Projeto

O `sys_tdm` é um sistema desenvolvido para gerenciar orçamentos, permitindo a criação, edição e exportação de orçamentos para o formato Excel. Ele lida com a complexidade de diferentes tipos de produtos (Portas, Armários, Pavimentos) e suas respectivas medidas e formatações.

## Funcionalidades

- Criação e edição de orçamentos.
- Gerenciamento de itens de orçamento com categorias, templates e instâncias de produtos.
- Exportação de orçamentos para arquivos Excel (`.xlsx`) com formatação detalhada e preservação de cláusulas contratuais.
- Suporte a diferentes tipos de produtos com atributos variados (largura, altura, profundidade, etc.).

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
