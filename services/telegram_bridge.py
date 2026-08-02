import os
import sys
import asyncio
import logging
import subprocess
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Carregar variáveis de ambiente (.env)
load_dotenv()

# Configuração de Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("AntigravityBridge")

# Credenciais e Segurança
DEV_BOT_TOKEN = os.getenv("TELEGRAM_DEV_BOT_TOKEN") or os.getenv("bot_token")
AUTH_USER_ID_RAW = os.getenv("AUTHORIZED_USER_ID") or os.getenv("chat_id")

try:
    AUTHORIZED_USER_ID = int(AUTH_USER_ID_RAW) if AUTH_USER_ID_RAW else None
except ValueError:
    AUTHORIZED_USER_ID = None

WORKSPACE_DIR = Path(__file__).resolve().parent.parent
BRAIN_DIR = Path.home() / ".gemini" / "antigravity-ide" / "brain"

# Estado de espera para comentários do usuário
WAITING_FOR_COMMENT = {}


def restricted(func):
    """Decorator para permitir o uso do bot apenas pelo usuário autorizado."""
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if AUTHORIZED_USER_ID and user_id != AUTHORIZED_USER_ID:
            logger.warning(f"⚠️ Acesso não autorizado negado para o ID: {user_id}")
            if update.message:
                await update.message.reply_text("⛔ **Acesso Negado.** Seu ID não está autorizado.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ Acesso não autorizado.", show_alert=True)
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


def find_latest_plan() -> Path | None:
    """Busca o arquivo implementation_plan.md mais recente na workspace ou na pasta brain."""
    candidates = []
    
    # Busca na pasta brain do antigravity-ide
    if BRAIN_DIR.exists():
        for p in BRAIN_DIR.glob("**/implementation_plan.md"):
            candidates.append(p)
            
    # Busca na workspace local
    local_plan = WORKSPACE_DIR / "implementation_plan.md"
    if local_plan.exists():
        candidates.append(local_plan)

    if not candidates:
        return None
        
    # Ordena por data de modificação
    candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return candidates[0]


def find_latest_walkthrough() -> Path | None:
    """Busca o arquivo walkthrough.md mais recente."""
    candidates = []
    if BRAIN_DIR.exists():
        for p in BRAIN_DIR.glob("**/walkthrough.md"):
            candidates.append(p)
    local_wt = WORKSPACE_DIR / "walkthrough.md"
    if local_wt.exists():
        candidates.append(local_wt)

    if not candidates:
        return None
    candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return candidates[0]


@restricted
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start ou /help - Menu Principal."""
    msg = (
        "🤖 **Antigravity Mobile Bridge Ativo!**\n\n"
        "Comandos disponíveis:\n"
        "📋 `/plan` - Visualizar e aprovar o Implementation Plan\n"
        "📝 `/walkthrough` - Visualizar o relatório de tarefas (Walkthrough)\n"
        "📊 `/status` - Ver status do Git e do robô SpotBot Pro\n"
        "🔍 `/diff` - Ver alterações pendentes no código\n"
        "💬 `/prompt <texto>` - Enviar novo comando/instrução para a workspace\n"
        "📋 `/logs` - Ver últimos logs do robô\n"
    )
    keyboard = [
        [
            InlineKeyboardButton("📋 Ver Plano Atual", callback_data="show_plan"),
            InlineKeyboardButton("📊 Status Git", callback_data="show_status")
        ],
        [
            InlineKeyboardButton("🔍 Ver Diffs de Código", callback_data="show_diff"),
            InlineKeyboardButton("📝 Walkthrough", callback_data="show_walkthrough")
        ]
    ]
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


@restricted
async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o Implementation Plan atual com botões de aprovação."""
    plan_path = find_latest_plan()
    if not plan_path or not plan_path.exists():
        await update.message.reply_text("📂 **Nenhum Implementation Plan encontrado no momento.**")
        return

    content = plan_path.read_text(encoding="utf-8")
    
    # Limitar tamanho para o limite do Telegram (4000 caracteres)
    trimmed_content = content[:3500] + ("\n\n*(Conteúdo truncado...)*" if len(content) > 3500 else "")

    keyboard = [
        [
            InlineKeyboardButton("✅ Aprovar Plano", callback_data="approve_plan"),
            InlineKeyboardButton("💬 Aprovar com Comentários", callback_data="approve_comment"),
        ],
        [
            InlineKeyboardButton("❌ Rejeitar Plano", callback_data="reject_plan")
        ]
    ]

    await update.message.reply_text(
        f"📋 **Implementation Plan Atual:**\n\n{trimmed_content}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@restricted
async def walkthrough_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o Walkthrough do projeto."""
    wt_path = find_latest_walkthrough()
    if not wt_path or not wt_path.exists():
        await update.message.reply_text("📄 **Nenhum relatório Walkthrough encontrado no momento.**")
        return

    content = wt_path.read_text(encoding="utf-8")
    trimmed_content = content[:3500] + ("\n\n*(Conteúdo truncado...)*" if len(content) > 3500 else "")
    await update.message.reply_text(f"📝 **Walkthrough de Execução:**\n\n{trimmed_content}", parse_mode="Markdown")


@restricted
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o status do Git no repositório."""
    try:
        res = subprocess.run(["git", "status", "-s"], capture_output=True, text=True, cwd=str(WORKSPACE_DIR))
        branch = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, cwd=str(WORKSPACE_DIR)).stdout.strip()
        status_text = res.stdout if res.stdout else "Nenhuma alteração pendente (Workspace limpo)."
        msg = f"📊 **Status do Git (Branch: `{branch}`)**\n\n```\n{status_text[:3500]}\n```"
    except Exception as e:
        msg = f"⚠️ Erro ao obter status do Git: {e}"
    
    await update.message.reply_text(msg, parse_mode="Markdown")


@restricted
async def diff_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe o git diff das alterações pendentes."""
    try:
        res = subprocess.run(["git", "diff"], capture_output=True, text=True, cwd=str(WORKSPACE_DIR))
        diff_text = res.stdout if res.stdout else "Nenhuma modificação de arquivo não commitada."
        msg = f"🔍 **Git Diff Pendente:**\n\n```diff\n{diff_text[:3500]}\n```"
    except Exception as e:
        msg = f"⚠️ Erro ao obter git diff: {e}"
    
    await update.message.reply_text(msg, parse_mode="Markdown")


async def query_gemini_ai(prompt: str) -> str:
    """Consulta a IA Gemini com o contexto do projeto e retorna a resposta."""
    gemini_key = os.getenv("gemini_api") or os.getenv("GEMINI_API_KEY") or os.getenv("gemini_api_key")
    if not gemini_key:
        return "⚠️ Chave API do Gemini (`gemini_api`) não encontrada no arquivo `.env`."
    
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=gemini_key)
        
        instr_file = WORKSPACE_DIR / "gemini_instructions.txt"
        sys_instruction = (
            "Você é a IA assistente do projeto SpotBot Pro / Antigravity.\n"
            "Responda sempre em Português do Brasil (pt-BR) de forma direta, clara, elegante e tecnicamente precisa.\n"
        )
        if instr_file.exists():
            sys_instruction += f"\nInstruções do Projeto:\n{instr_file.read_text(encoding='utf-8')[:1500]}\n"

        config = types.GenerateContentConfig(
            system_instruction=sys_instruction,
            temperature=0.7,
            top_p=0.95,
            max_output_tokens=4096
        )
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config
            )
        )
        if response and response.text:
            return response.text
        return "⚠️ Não foi possível obter uma resposta da IA."
    except Exception as e:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=gemini_key)
            config = types.GenerateContentConfig(
                system_instruction=sys_instruction,
                temperature=0.7,
                top_p=0.95,
                max_output_tokens=4096
            )
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt,
                    config=config
                )
            )
            if response and response.text:
                return response.text
        except Exception as err2:
            logger.error(f"Erro ao consultar Gemini AI: {err2}")
        return f"⚠️ Erro ao consultar a IA Gemini: {e}"


@restricted
async def prompt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe um prompt via Telegram, salva o registro e responde usando a IA Gemini."""
    if not context.args:
        await update.message.reply_text("💡 **Uso:** `/prompt <sua mensagem ou dúvida aqui>`")
        return

    instruction = " ".join(context.args)
    prompt_file = WORKSPACE_DIR / "MOBILE_PROMPTS.md"
    
    with open(prompt_file, "a", encoding="utf-8") as f:
        f.write(f"\n- [{update.message.date.strftime('%Y-%m-%d %H:%M:%S')}] {instruction}\n")

    status_msg = await update.message.reply_text("🧠 *Analisando com Antigravity IA...*", parse_mode="Markdown")

    ai_reply = await query_gemini_ai(instruction)
    
    # Se a resposta for grande, divide para o limite do Telegram
    if len(ai_reply) > 4000:
        await status_msg.edit_text(ai_reply[:4000])
        for chunk in [ai_reply[i:i+4000] for i in range(4000, len(ai_reply), 4000)]:
            await update.message.reply_text(chunk)
    else:
        try:
            await status_msg.edit_text(ai_reply, parse_mode="Markdown")
        except Exception:
            await status_msg.edit_text(ai_reply)


@restricted
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manipula interações com os botões inline do Telegram."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "show_plan":
        plan_path = find_latest_plan()
        if plan_path and plan_path.exists():
            content = plan_path.read_text(encoding="utf-8")[:3500]
            keyboard = [
                [InlineKeyboardButton("✅ Aprovar Plano", callback_data="approve_plan"), InlineKeyboardButton("💬 Comentar", callback_data="approve_comment")],
                [InlineKeyboardButton("❌ Rejeitar Plano", callback_data="reject_plan")]
            ]
            await query.message.reply_text(f"📋 **Implementation Plan:**\n\n{content}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.message.reply_text("📂 Nenhum plano encontrado.")

    elif query.data == "show_status":
        res = subprocess.run(["git", "status", "-s"], capture_output=True, text=True, cwd=str(WORKSPACE_DIR))
        await query.message.reply_text(f"📊 **Status Git:**\n```\n{res.stdout or 'Workspace limpo'}\n```", parse_mode="Markdown")

    elif query.data == "show_diff":
        res = subprocess.run(["git", "diff"], capture_output=True, text=True, cwd=str(WORKSPACE_DIR))
        await query.message.reply_text(f"🔍 **Diff:**\n```diff\n{(res.stdout or 'Sem alterações')[:3500]}\n```", parse_mode="Markdown")

    elif query.data == "show_walkthrough":
        wt_path = find_latest_walkthrough()
        if wt_path and wt_path.exists():
            await query.message.reply_text(f"📝 **Walkthrough:**\n\n{wt_path.read_text(encoding='utf-8')[:3500]}", parse_mode="Markdown")
        else:
            await query.message.reply_text("📄 Nenhum walkthrough encontrado.")

    elif query.data == "approve_plan":
        try:
            # Executa git add, commit e push automaticamente para disparar a build no Railway
            subprocess.run(["git", "add", "."], check=True, cwd=str(WORKSPACE_DIR))
            commit_res = subprocess.run(["git", "commit", "-m", "feat: plano aprovado via Telegram Mobile Bridge"], capture_output=True, text=True, cwd=str(WORKSPACE_DIR))
            push_res = subprocess.run(["git", "push", "origin", "master"], capture_output=True, text=True, cwd=str(WORKSPACE_DIR))
            
            await query.edit_message_text(
                "✅ **Plano Aprovado e Aplicado com Sucesso!**\n\n"
                "🚀 Alterações commitadas e enviadas para o GitHub `master`.\n"
                "☁️ Railway disparou o deploy automático de produção!"
            )
        except Exception as e:
            await query.message.reply_text(f"⚠️ Erro ao aplicar/pushar plano: {e}")

    elif query.data == "approve_comment":
        WAITING_FOR_COMMENT[user_id] = True
        await query.message.reply_text("💬 **Por favor, digite o seu comentário/ajuste para o plano:**")

    elif query.data == "reject_plan":
        await query.edit_message_text("❌ **Plano Rejeitado.** Aguardando novos ajustes ou solicitações.")


@restricted
async def handle_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe mensagens de texto normais (respostas com comentários ou conversas diretas com a IA)."""
    user_id = update.effective_user.id
    user_text = update.message.text

    # Se estiver aguardando comentário de aprovação do plano
    if WAITING_FOR_COMMENT.get(user_id):
        WAITING_FOR_COMMENT[user_id] = False
        
        prompt_file = WORKSPACE_DIR / "MOBILE_PROMPTS.md"
        with open(prompt_file, "a", encoding="utf-8") as f:
            f.write(f"\n- [Comentário de Aprovação - {update.message.date.strftime('%Y-%m-%d %H:%M:%S')}] {user_text}\n")
            
        try:
            subprocess.run(["git", "add", "."], check=True, cwd=str(WORKSPACE_DIR))
            subprocess.run(["git", "commit", "-m", f"feat: plano aprovado com comentario via Telegram: {user_text}"], capture_output=True, text=True, cwd=str(WORKSPACE_DIR))
            subprocess.run(["git", "push", "origin", "master"], capture_output=True, text=True, cwd=str(WORKSPACE_DIR))
            
            await update.message.reply_text(
                f"✅ **Plano Aprovado com Comentário!**\n\n"
                f"💬 Comentário registrado: *\"{user_text}\"*\n"
                f"🚀 Commit & Push para o GitHub efetuados (Railway atualizado)."
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Erro ao registrar aprovação com comentário: {e}")
        return

    # Caso contrário: conversar diretamente com a IA Gemini!
    prompt_file = WORKSPACE_DIR / "MOBILE_PROMPTS.md"
    with open(prompt_file, "a", encoding="utf-8") as f:
        f.write(f"\n- [{update.message.date.strftime('%Y-%m-%d %H:%M:%S')}] {user_text}\n")

    status_msg = await update.message.reply_text("🧠 *Analisando sua mensagem com Antigravity IA...*", parse_mode="Markdown")

    ai_reply = await query_gemini_ai(user_text)

    if len(ai_reply) > 4000:
        await status_msg.edit_text(ai_reply[:4000])
        for chunk in [ai_reply[i:i+4000] for i in range(4000, len(ai_reply), 4000)]:
            await update.message.reply_text(chunk)
    else:
        try:
            await status_msg.edit_text(ai_reply, parse_mode="Markdown")
        except Exception:
            await status_msg.edit_text(ai_reply)


class PlanFileHandler(FileSystemEventHandler):
    """File Watcher para enviar o Implementation Plan automaticamente quando for criado/alterado."""
    def __init__(self, loop, app, chat_id):
        self.loop = loop
        self.app = app
        self.chat_id = chat_id
        self._last_notified = 0

    def on_modified(self, event):
        if event.src_path.endswith("implementation_plan.md"):
            now = asyncio.get_event_loop().time() if self.loop.is_running() else 0
            if now - self._last_notified < 5:  # Debounce de 5 segundos
                return
            self._last_notified = now
            
            asyncio.run_coroutine_threadsafe(
                self.notify_plan_updated(event.src_path),
                self.loop
            )

    async def notify_plan_updated(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()[:3500]
                
            keyboard = [
                [InlineKeyboardButton("✅ Aprovar Plano", callback_data="approve_plan"), InlineKeyboardButton("💬 Comentar", callback_data="approve_comment")],
                [InlineKeyboardButton("❌ Rejeitar Plano", callback_data="reject_plan")]
            ]
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=f"🔔 **Novo Implementation Plan Disponível!**\n\n{content}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Erro ao enviar notificação de novo plano: {e}")


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    if not DEV_BOT_TOKEN or DEV_BOT_TOKEN == "SEU_BOT_TOKEN_TELEGRAM_AQUI":
        logger.error("❌ TELEGRAM_DEV_BOT_TOKEN não configurado no arquivo .env!")
        print("Erro: Por favor, adicione TELEGRAM_DEV_BOT_TOKEN=seu_token no arquivo .env")
        sys.exit(1)

    print("🚀 Iniciando Antigravity Mobile Telegram Bridge...")
    app = ApplicationBuilder().token(DEV_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(CommandHandler("plan", plan_command))
    app.add_handler(CommandHandler("walkthrough", walkthrough_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("diff", diff_command))
    app.add_handler(CommandHandler("prompt", prompt_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_input))

    # Iniciar File Watcher para notificar quando novos planos forem gerados
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if AUTHORIZED_USER_ID:
        event_handler = PlanFileHandler(loop, app, AUTHORIZED_USER_ID)
        observer = Observer()
        if BRAIN_DIR.exists():
            observer.schedule(event_handler, str(BRAIN_DIR), recursive=True)
        observer.schedule(event_handler, str(WORKSPACE_DIR), recursive=False)
        observer.start()
        print("👁️ File Watcher ativado para monitorar novos Implementation Plans.")

    print("🤖 Bot Telegram dev ouvindo mensagens. Pressione Ctrl+C para encerrar.")
    app.run_polling()


if __name__ == "__main__":
    main()
