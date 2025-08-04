# SysOrc - Sistema Integrado de Gestão de Orçamentos, Produtos e Consumos

## Descrição do Projeto

O SysOrc é um sistema web integrado desenvolvido para otimizar a gestão de processos de orçamentação, catalogação de produtos com configurações avançadas e rastreamento detalhado de consumos de materiais e tempo de trabalho. Construído com Django, o sistema visa proporcionar uma ferramenta robusta para empresas que necessitam de controle preciso sobre seus custos de produção e recursos.

## Funcionalidades

### Módulo de Orçamentos
- **Criação e Edição de Orçamentos**: Gerencie orçamentos com adição e remoção dinâmica de itens.
- **Descrições Dinâmicas**: Crie descrições de itens e configurações baseadas em templates, que são preenchidas automaticamente com os atributos e componentes do produto.
- **Cálculos Automáticos**: Valores por item e total do orçamento calculados em tempo real.
- **Versionamento de Orçamentos**: Crie novas versões de orçamentos existentes para rastreamento de revisões.
- **Exportação para Excel**: Gere documentos de orçamento detalhados e fichas de produção em formato `.xlsx` com formatação aprimorada e descrições de componentes detalhadas. Inclui a opção de exportar modelos para impressão.
- **Gestão de Preços e Margens**: Ferramentas para definir preços unitários com base em custos de fabricação e margens de negócio.
- **Arquitetura de Configuração de Produto**: Suporte a variações complexas de produtos através de configurações e componentes.

### Módulo de Produtos
- **Catálogo de Produtos e Componentes**: Gerencie categorias, atributos, templates de produtos e componentes.
- **Configurações de Produto**: Defina configurações específicas para produtos, permitindo variações de componentes e atributos. Inclui funcionalidade de filtragem por nome/descrição e categoria.
- **Instâncias de Produto**: Crie instâncias de produtos com base em templates e configurações, com atributos e componentes calculados dinamicamente. Inclui funcionalidade de filtragem por código/configuração, categoria e nome do orçamento associado, além de exibir o nome do orçamento.
- **Documentação Interna**: Modelos (`models.py`), formulários (`forms.py`), views (`views.py`) e configurações de admin (`admin.py`) agora incluem docstrings detalhadas para maior clareza e manutenibilidade do código.

### Módulo de Estoque
- **Gestão Abrangente de Itens**:
    - **Categorias de Itens**: Gerencie categorias hierárquicas para organizar itens estocáveis.
    - **Itens Estocáveis**: Adicione e configure itens físicos com códigos internos gerados automaticamente, SKUs de fornecedores e detalhes dimensionais.
    - **Lotes**: Controle a entrada de itens em estoque por lotes, com rastreamento de quantidade inicial, quantidade atual e custo unitário de compra (FIFO).
    - **Movimentações de Estoque**: Registre detalhadamente todas as transações (entradas, saídas, ajustes) para rastreabilidade completa.
- **Ajuste de Estoque**: Permite ajustar manualmente as quantidades de itens em estoque, registrando movimentos de ajuste (positivo ou negativo) para histórico e correção de inventário.
- **Integração com Consumo**: Saídas de estoque são automaticamente registradas quando itens são consumidos em fichas de obra.

### Módulo de Consumos
- **Dashboard de KPIs**: Visualize indicadores de performance chave, como tempo de produção por posto e operador, tempo médio por operação e detalhes de consumo por obra. Inclui endpoints de API para integração.
- **Registro de Consumo de Material**: Rastreie o consumo de matéria-prima e componentes por obra. O relatório de consumo de material foi aprimorado com paginação e referências corretas aos itens estocáveis.
- **Registro de Sessões de Trabalho**: Monitore o uso de máquinas e o tempo de trabalho de operadores em postos específicos. O relatório de utilização de máquinas foi aprimorado com paginação.
- **Gestão de Postos de Trabalho e Operadores**: Cadastre e gerencie os recursos humanos e máquinas da fábrica.
- **Relatórios de Consumo**: Visualize relatórios agregados de consumo de material e utilização de máquinas, com opção de exportação para Excel e agora também para modelos de impressão.

## Tecnologias Utilizadas

- **Backend**: Python, Django
- **Banco de Dados**: PostgreSQL (configurado via Docker)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5, Crispy Forms, Select2 (para campos de seleção aprimorados)
- **Containerização**: Docker, Docker Compose
- **Manipulação de Excel**: OpenPyXL

## Configuração do Ambiente

Este projeto utiliza Docker para facilitar a configuração do ambiente de desenvolvimento e produção.

1.  **Pré-requisitos:**
    *   Docker Desktop (ou Docker Engine e Docker Compose) instalado.
    *   Git instalado.

2.  **Clonar o Repositório:**
    ```bash
    git clone https://github.com/lucascvalle/sys_tdm.git
    cd sys_tdm
    ```

3.  **Construir e Iniciar os Contêineres:**
    ```bash
    docker-compose up --build -d
    ```
    O `-d` executa os contêineres em segundo plano.

4.  **Executar Migrações do Banco de Dados:**
    Após os contêineres estarem rodando, você precisará executar as migrações do Django para configurar o banco de dados:
    ```bash
    docker-compose exec web python sys_tdm/manage.py migrate
    ```

5.  **Criar Superusuário (Opcional, para acesso ao Admin):**
    ```bash
    docker-compose exec web python sys_tdm/manage.py createsuperuser
    ```
    Siga as instruções no terminal para criar seu usuário administrador.

## Uso

Após a configuração, o sistema estará acessível em `http://localhost:8000` (ou a porta configurada no seu `docker-compose.yml`).

-   **Página Inicial**: `http://localhost:8000`
-   **Acessar o Admin**: `http://localhost:8000/admin`
-   **Módulo de Orçamentos**: `http://localhost:8000/orcamentos/`
-   **Módulo de Produtos**: `http://localhost:8000/produtos/`
-   **Módulo de Consumos**: `http://localhost:8000/consumos/`
-   **Módulo de Estoque**: `http://localhost:8000/estoque/`

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues e pull requests.

## Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.