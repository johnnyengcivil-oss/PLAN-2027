# Instalação

> **Conferir a qualquer momento:** `python verificar.py` diz, passo a passo,
> o que já está pronto e o que falta — com o comando exato de cada pendência.

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

Durante o desenvolvimento, com Python 3.10+ instalado:

```bat
cd C:\BANCO_COMPOSICOES
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

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

### 3a. Importação automática (recomendado)

```bat
cscript //nologo instalar_vba.vbs
```

O script abre o Excel via COM, importa os dez módulos de `vba\`, cria os
botões e salva como `Sistema_Composicoes.xlsm`.

Exige a opção **"Confiar no acesso ao modelo de objeto do projeto do VBA"**,
em *Arquivo → Opções → Central de Confiabilidade → Configurações da Central
de Confiabilidade → Configurações de Macro*. É uma caixa de seleção do
próprio Excel, marcável por usuário comum. Se preferir não habilitá-la,
use o passo 3b.

### 3b. Importação manual (2 minutos, sem alterar nenhuma configuração)

1. Abra `Sistema_Composicoes.xlsx` no Excel.
2. **Arquivo → Salvar como** → tipo **Pasta de Trabalho Habilitada para
   Macro (*.xlsm)** → nome `Sistema_Composicoes`.
3. `Alt+F11` para abrir o editor VBA.
4. **Arquivo → Importar Arquivo** (`Ctrl+M`) e selecione, um a um, os dez
   arquivos de `vba\`:

   ```
   modJson.bas          modPythonBridge.bas   modUtils.bas
   modMain.bas          modUI.bas             modServices.bas
   modCompositions.bas  modMaterials.bas      modConfig.bas
   modDatabaseUI.bas
   ```

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
