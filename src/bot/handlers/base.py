import asyncio
from pathlib import Path
from subprocess import PIPE

from aiogram import F, Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.chat_action import ChatActionSender

from claude_code_sdk import AssistantMessage, TextBlock, query, ClaudeCodeOptions

from database.models import User
from bot.states import AddProjectStates

router = Router()


@router.message(CommandStart())
async def start_message(message: types.Message, user: User) -> None:
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[[types.KeyboardButton(text="Projects"), types.KeyboardButton(text="Add project")]],
    )
    await message.answer(text=f"Hello, {user.fullname}.", reply_markup=keyboard)


@router.message(F.text == "Add project")
async def add_project_prompt(message: types.Message, state: FSMContext) -> None:
    await state.set_state(AddProjectStates.waiting_for_url)
    await message.answer("Send me the project repository URL")


@router.message(AddProjectStates.waiting_for_url)
async def add_project_clone(message: types.Message, state: FSMContext) -> None:
    if not message.text:
        return
    repo_url = message.text.strip()
    projects_dir = Path("projects")
    projects_dir.mkdir(exist_ok=True)

    async with ChatActionSender.typing(chat_id=message.chat.id, bot=message.bot):
        process = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            repo_url,
            cwd=projects_dir,
            stdout=PIPE,
            stderr=PIPE,
        )
        stdout, stderr = await process.communicate()

    if process.returncode == 0:
        text = "Project cloned successfully"
    else:
        text = f"Failed to clone project (code {process.returncode}).\n{stderr.decode()}"
    await state.clear()
    await message.answer(text)


@router.message(F.text == "Projects")
async def list_projects(message: types.Message) -> None:
    projects_dir = Path("projects")
    if not projects_dir.exists():
        await message.answer("No projects added yet")
        return
    projects = [p.name for p in projects_dir.iterdir() if p.is_dir()]
    if not projects:
        await message.answer("No projects added yet")
        return
    await message.answer("Projects:\n" + "\n".join(projects))


@router.message()
async def claude_code_handler(message: types.Message) -> None:
    if not message.text:
        return

    options = ClaudeCodeOptions(allowed_tools=["Read", "Write"])
    result_chunks: list[str] = []

    async with ChatActionSender.typing(chat_id=message.chat.id, bot=message.bot):
        async for msg in query(prompt=message.text, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        result_chunks.append(block.text)

    if result_chunks:
        await message.answer("\n".join(result_chunks))
