import shutil
import subprocess
import tempfile
import os
import re
import zipfile
from enum import Enum
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse

app = FastAPI(title="LaTeX Conversion API")

# Define where your assets live in the container
ASSETS_DIR = Path(__file__).parent / "latex_assets"

class ConversionFormat(str, Enum):
    PDF = "pdf"
    MARKDOWN = "markdown"

def sanitize_filename(name: str) -> str:
    name = os.path.basename(name)
    name = re.sub(r'[^a-zA-Z0-9_\-\. ]', '', name)
    if not name:
        return "document"
    return name

class LatexConverter:
    
    @staticmethod
    def _inject_assets(directory: Path):
        """
        Copies all default .cls, .sty, and image files from latex_assets 
        into the temp directory.
        """
        if not ASSETS_DIR.exists():
            print("Warning: latex_assets directory not found.")
            return

        for item in ASSETS_DIR.iterdir():
            if item.is_file():
                destination = directory / item.name
                # Only copy if the user hasn't already uploaded their own version
                if not destination.exists():
                    shutil.copy2(item, destination)

    @staticmethod
    def _save_upload_file(upload_file: UploadFile, directory: Path) -> Path:
        """
        1. Injects default assets (resume.cls, logos, etc.)
        2. Saves the uploaded file.
        """
        # A. Inject Assets First
        LatexConverter._inject_assets(directory)

        # B. Save User File
        filename = upload_file.filename
        file_path = directory / filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        
        return file_path

    @staticmethod
    def _extract_and_find_tex(zip_path: Path, directory: Path) -> Path:
        """Extracts zip and finds the most likely main .tex file."""
        # A. Inject Assets (in case they unzip into a subfolder, we inject at root)
        LatexConverter._inject_assets(directory)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(directory)
        
        # Logic to find .tex file (same as before)
        if (directory / "main.tex").exists():
            return directory / "main.tex"
        
        zip_stem = zip_path.stem
        if (directory / f"{zip_stem}.tex").exists():
            return directory / f"{zip_stem}.tex"

        tex_files = list(directory.glob("*.tex"))
        if tex_files:
            return tex_files[0]
            
        raise HTTPException(status_code=400, detail="No .tex file found in the ZIP archive.")

    @staticmethod
    def to_pdf(input_path: Path, output_dir: Path) -> Path:
        try:
            # Tectonic needs to run in the directory of the file to find the injected .cls
            cmd = [
                "tectonic",
                str(input_path),
                "--outdir", str(output_dir),
                "--print", 
                "--keep-intermediates"
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=input_path.parent)
            return output_dir / f"{input_path.stem}.pdf"
        except subprocess.CalledProcessError as e:
            error_log = e.stderr.decode("utf-8")
            raise HTTPException(status_code=422, detail=f"LaTeX Compilation Failed:\n{error_log}")

    @staticmethod
    def to_markdown(input_path: Path, output_dir: Path) -> Path:
        import pypandoc
        output_path = output_dir / "output.md"
        try:
            pypandoc.convert_file(
                str(input_path),
                'gfm',
                outputfile=str(output_path),
                format='latex',
                extra_args=['--wrap=none', f'--resource-path={input_path.parent}']
            )
            return output_path
        except RuntimeError as e:
            raise HTTPException(status_code=422, detail=f"Pandoc Conversion Failed:\n{str(e)}")

def cleanup_temp_dir(path: str):
    shutil.rmtree(path, ignore_errors=True)

@app.post("/convert/{target_format}")
async def convert_latex(
    target_format: ConversionFormat,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    output_filename: Optional[str] = Query(None)
):
    if not (file.filename.endswith(".tex") or file.filename.endswith(".zip")):
        raise HTTPException(status_code=400, detail="Only .tex or .zip files are supported")

    if output_filename:
        download_name = sanitize_filename(output_filename)
    else:
        download_name = Path(file.filename).stem

    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)

    try:
        # 1. Save uploaded file (Auto-injects resume.cls here!)
        saved_file_path = LatexConverter._save_upload_file(file, temp_path)
        
        if file.filename.endswith(".zip"):
            input_path = LatexConverter._extract_and_find_tex(saved_file_path, temp_path)
        else:
            input_path = saved_file_path

        # 2. Convert
        if target_format == ConversionFormat.PDF:
            result_path = LatexConverter.to_pdf(input_path, temp_path)
            media_type = "application/pdf"
            final_filename = f"{download_name}.pdf"
        elif target_format == ConversionFormat.MARKDOWN:
            result_path = LatexConverter.to_markdown(input_path, temp_path)
            media_type = "text/markdown"
            final_filename = f"{download_name}.md"
        
        # 3. Rename
        final_path = temp_path / final_filename
        if result_path != final_path:
            result_path.rename(final_path)

        background_tasks.add_task(cleanup_temp_dir, temp_dir)

        return FileResponse(path=final_path, filename=final_filename, media_type=media_type)

    except Exception as e:
        cleanup_temp_dir(temp_dir)
        raise e
