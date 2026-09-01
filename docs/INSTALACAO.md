# Instalação

> **Caminho mais curto:** duplo clique em `COMECAR_AQUI.bat`. Ele executa
> as três etapas — ambiente, bases e planilha — sem digitar nada.
>
> **Conferir a qualquer momento:** duplo clique em `verificar.bat`. Diz,
> passo a passo, o que já está pronto e o que falta, com o comando exato
> de cada pendência.

Requisitos: Windows com Excel, **usuário comum** — nenhuma etapa pede
privilégio de administrador, serviço, driver ou escrita em `Program Files`
(item 62).

---

## 0. Obter os arquivos

```bat
git clone -b claude/excel-vba-python-composicoes-f40k5d ^
    https://github.com/johnnyengcivil-oss/PLAN-2027.git C:\BANCO_COMPOSICOES
```

Sem Git: baixe o ZIP do branch pelo GitHub (**Code → Download ZIP**) e
extraia para `C:\BANCO_COMPOSICOES`.

As cinco bases **não vêm no repositório** — são dados proprietários de
preço, atualizados periodicamente. Você as copia no passo 1.

---

## 1. Estrutura da pasta

Copie tudo para uma pasta única, por exemplo `C:\BANCO_COMPOSICOES\`:

```
BANCO_COMPOSICOES\
├── Sistema_Composicoes.xlsm      (gerado no passo 3)
├── BASES\
│   ├── <base de serviços>.xlsx
│   ├── MATERIAIS.xlsx
│   ├── <EDIF>.xls
│   ├── <INFRA>.xls
│   └── <AUXILIARES>.xls
├── python\                        (durante o desenvolvimento)
│   ├── main.py
│   └── motor\
├── vba\                           (fontes VBA versionadas)
├── banco_composicoes.db           (criado na primeira execução)
├── config.json                    (criado ao salvar configurações)
└── log.txt
```

As bases também funcionam soltas na raiz — o sistema procura em `BASES\`
e depois na própria pasta. **Os arquivos não precisam ter nome nenhum em
particular:** EDIF, INFRA e AUX são identificados pelo conteúdo.

Todos os caminhos derivam de `ThisWorkbook.Path`. Nada depende de
`C:\Users\<nome>\`, então a pasta pode ser movida ou copiada para a rede.

---

## 2. Python

### Não tenho Python — e agora?

**No pacote entregue ao usuário, o Python já vai dentro**, em
`python-portatil\`, com as bibliotecas instaladas nele. Não há nada a
fazer. Esta seção vale para quem monta o pacote a partir do repositório.

Duas saídas. A primeira **não instala nada** no Windows.

**Portátil (recomendada).** Baixe
[`python-3.11.9-embed-amd64.zip`](https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip)
(~10 MB) e extraia o conteúdo numa pasta `python-portatil\` criada ao lado
do `COMECAR_AQUI.bat`, de modo a existir `python-portatil\python.exe`.
Os scripts detectam e usam — inclusive se o Windows tiver criado uma
subpasta ao extrair (`python-portatil\python-3.11.9-embed-amd64\`), erro
comum que o `_localizar_python.bat` trata. Não mexe no registro, não pede
administrador, e desinstalar é apagar a pasta.

Depois de extrair, rode `preparar_libs.py` com ele uma vez: o Python
embeddable vem com o `site-packages` **desligado** por um arquivo `._pth`,
e é esse script que corrige o arquivo e instala as bibliotecas de `libs\`
sem precisar de pip.

**Instalar normalmente.** [python.org/downloads](https://www.python.org/downloads/),
marcando **"Add Python to PATH"** na primeira tela — vem desmarcada, e é a
causa nº 1 de o Windows não achar o Python depois.

As bibliotecas vêm prontas em `libs\`, então a instalação delas **não
precisa de internet**. `preparar_libs.py` usa `pip --no-index` quando há
pip e, quando não há — o caso do Python portátil —, extrai as rodas
direto no `site-packages`.

### Caminho fácil — duplo clique

Dê **duplo clique em `instalar.bat`**. Ele procura o Python, cria o
ambiente isolado, instala as bibliotecas e roda a verificação, mostrando o
que falta. Não é preciso abrir o Prompt de Comando nem digitar nada, e não
exige privilégio de administrador.

Se o Python não estiver instalado, o script diz isso e indica onde baixar.
Ao instalar, **marque "Add Python to PATH"** na primeira tela.

Há ainda `verificar.bat` (reconferir a instalação) e `prova.bat` (rodar a
prova funcional), ambos por duplo clique.

### Caminho manual — pelo Prompt de Comando

Com Python 3.10+ instalado:

```bat
cd C:\BANCO_COMPOSICOES
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Se `python` não for reconhecido, use `py -3` no lugar — é o lançador do
Windows, e evita o atalho da Microsoft Store que abre a loja em vez de
executar o Python.

O `modPythonBridge` procura o interpretador nesta ordem:

1. `motor.exe` na raiz (versão empacotada);
2. `motor\motor.exe` (PyInstaller `--onedir`);
3. `.venv\Scripts\python.exe` + `python\main.py`;
4. `python` do PATH.

Confira o que está pronto:

```bat
.venv\Scripts\python verificar.py
```

Ele percorre dependências, bases, banco, motor e interface, e imprime o
comando exato de cada pendência. Devolve código de saída 0 quando o
sistema está pronto.

### Camada semântica opcional

O sistema já funciona sem instalar mais nada: o backend padrão é
TF-IDF com n-gramas de caractere, local e determinístico, sem download.

Para usar embeddings neurais, instale e mude `backend_semantico` para
`sentence_transformers` em `config.json`:

```bat
.venv\Scripts\python -m pip install sentence-transformers
```

O primeiro uso baixa o modelo (~120 MB) uma única vez. Depois disso o
funcionamento é offline. Nenhuma API paga é usada em qualquer configuração
(item 45).

---

## 3. Gerar a pasta de trabalho

```bat
.venv\Scripts\python build_xlsm.py
```

Isso gera `Sistema_Composicoes.xlsx` com as nove abas já formatadas.
Falta acrescentar o código VBA — e isso precisa do Excel, então é feito
uma única vez, na máquina do usuário.

### 3a. Automático — duplo clique em `MONTAR_PLANILHA.bat`

Ele gera o `.xlsx`, insere os dez módulos e salva `Sistema_Composicoes.xlsm`.

Para inserir os módulos, o Excel exige a opção **"Confiar no acesso ao
modelo de objeto do projeto do VBA"** — a chave `AccessVBOM` em
`HKEY_CURRENT_USER`. O script:

1. lê e guarda o valor atual;
2. **pede sua autorização** antes de mudar qualquer coisa;
3. liga a opção, monta a planilha;
4. **devolve a opção ao valor anterior**, inclusive se algo falhar.

Só afeta o seu usuário do Windows, não a máquina, e não exige
administrador. Se preferir não mexer nisso, responda `N`: o script então
mostra o caminho manual do passo 3b.

### 3b. Importação manual (2 minutos, sem alterar nenhuma configuração)

1. Abra `Sistema_Composicoes.xlsx` no Excel.
2. **Arquivo → Salvar como** → tipo **Pasta de Trabalho Habilitada para
   Macro (*.xlsm)** → nome `Sistema_Composicoes`.
3. `Alt+F11` para abrir o editor VBA.
4. Abra a pasta `vba\` no Explorador de Arquivos, selecione **os dez
   arquivos `.bas`** (`Ctrl+A`) e **arraste todos de uma vez** para a
   janela do editor, no painel esquerdo. É uma única arrastada — não
   precisa importar um a um.

5. Ainda no editor, `Ctrl+G` para abrir a janela Verificação Imediata,
   digite `modUI.ReconstruirBotoes` e pressione `Enter`. Os botões de
   todas as abas são criados.
6. Volte ao Excel e salve (`Ctrl+B`).

---

## 4. Primeira execução

1. Abra `Sistema_Composicoes.xlsm` e habilite as macros.
2. Na aba **INÍCIO**, clique **TESTAR MOTOR** — deve mostrar as contagens
   das bases.
3. Clique **ATUALIZAR BASES**. A primeira importação leva alguns segundos;
   as seguintes são instantâneas quando nada mudou (comparação por SHA-256).
4. Confira na aba **CONFIGURAÇÃO** se EDIF, INFRA e AUX foram identificados
   corretamente. A coluna *ARQUIVO DETECTADO* mostra o que o sistema achou
   e a tela INÍCIO mostra **como** cada um foi identificado.

Se algum arquivo não for reconhecido, escreva o nome dele em **C13** (EDIF),
**C14** (INFRA) ou **C15** (AUX) e clique **SALVAR CONFIGURAÇÃO**. A escolha
fica gravada em `config.json` e não precisa ser repetida (item 4).

---

## 5. Empacotamento para distribuição (item 61)

Depois de estabilizado, para rodar em máquinas sem Python:

```bat
.venv\Scripts\python -m pip install pyinstaller
.venv\Scripts\pyinstaller --onedir --name motor ^
    --paths python ^
    --collect-submodules motor ^
    python\main.py
```

Copie `dist\motor\` para dentro da pasta do sistema. O `modPythonBridge`
passa a usar `motor\motor.exe` automaticamente, sem alteração no VBA.

`--onefile` também funciona, mas descompacta a cada execução e deixa cada
chamada visivelmente mais lenta. Avalie só depois que `--onedir` estiver
validado.

---

## 6. As bases originais nunca são alteradas

Os cinco arquivos são abertos exclusivamente em modo de leitura
(`xlrd` e `openpyxl` com `read_only=True`). O sistema não grava, não
converte, não renomeia e não salva por cima. Toda transformação acontece
em memória e termina em `banco_composicoes.db`.

Se quiser garantir isso no sistema de arquivos, marque os cinco arquivos
como **somente leitura** nas propriedades do Windows — o sistema continua
funcionando normalmente.
