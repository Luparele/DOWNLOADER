# Video Downloader (Android)

Um aplicativo Android moderno e robusto para baixar vídeos das principais plataformas da internet, com uma interface neon clean e um motor de extração poderoso rodando localmente no próprio aparelho.

## 🚀 Funcionalidades

- **Multi-plataforma:** Baixa vídeos do YouTube, TikTok, Instagram, Twitter, Facebook e centenas de outros sites compatíveis com o `yt-dlp`.
- **Backend Python Integrado:** Utiliza o Chaquopy para embutir um servidor FastAPI local dentro do celular, comunicando-se nativamente com a interface Android (Kotlin).
- **Sem Resíduos (Storage Leak-free):** O aplicativo possui um mecanismo inteligente que remove arquivos fragmentados (`.part`) após interrupções de internet e limpa os originais do armazenamento interno invisível logo após a transferência bem-sucedida para a Galeria.
- **Organização:** Todos os downloads finalizados são salvos de forma limpa e visível na pasta nativa `Downloads/Video Downloader` do seu smartphone.
- **Design Moderno:** Interface escura baseada em neon verde, construída com HTML/CSS/JS dentro de uma WebView otimizada.

## 🛠️ Tecnologias Utilizadas

- **Frontend:** WebView, HTML5, CSS3, Vanilla JS
- **Android Native:** Kotlin, API Android, MediaStore
- **Motor Python:** Chaquopy, FastAPI, Uvicorn, yt-dlp, FFmpeg (via binários pré-compilados nativos)
- **Compilador:** Gradle (Kotlin DSL)

## 📦 Como Compilar

1. Clone o repositório.
2. Abra o projeto no **Android Studio**.
3. Aguarde o Gradle sincronizar todas as dependências (incluindo a instalação do Python via Chaquopy).
4. Rode o comando ou clique no play para instalar no emulador ou dispositivo físico:
   ```bash
   ./gradlew assembleDebug
   ```

## ⚠️ Aviso Legal e Termos de Uso

Este projeto foi construído inteiramente para fins educacionais e de estudo sobre a integração de Python (FastAPI/yt-dlp) de forma nativa em aplicativos Android via Chaquopy.
A responsabilidade sobre o conteúdo baixado através desta ferramenta é inteiramente do usuário final. O uso desta ferramenta para o download de materiais protegidos por direitos autorais, ou em quebra dos Termos de Serviço de qualquer plataforma (como o YouTube), é estritamente desencorajado.
