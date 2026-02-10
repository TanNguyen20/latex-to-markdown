# main.py
import shutil
import subprocess
import tempfile
import os
from enum import Enum
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

app = FastAPI(title="LaTeX Conversion API")

class ConversionFormat(str, Enum):
    PDF = "pdf"
    MARKDOWN = "markdown"

class LatexConverter:
    """
    Handles the logic for converting LaTeX files to different formats.
    Follows SRP (Single Responsibility Principle).
    """
    
    @staticmethod
    def _save_upload_file(upload_file: UploadFile, directory: Path) -> Path:
        """Saves the uploaded file to a temporary directory."""
        file_path = directory / "input.tex"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        return file_path

    @staticmethod
    def to_pdf(input_path: Path, output_dir: Path) -> Path:
        """
        Converts LaTeX to PDF using Tectonic.
        Tectonic automatically downloads packages and handles multiple passes.
        """
        try:
            # Tectonic command: tectonic input.tex --outdir /tmp/dir
            cmd = [
                "tectonic",
                str(input_path),
                "--outdir",
                str(output_dir),
                "--print",  # Print output to stdout
                "--keep-intermediates" # Optional: helps debug if needed
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Tectonic generates the pdf with the same name as input
            return output_dir / "input.pdf"
        
        except subprocess.CalledProcessError as e:
            error_log = e.stderr.decode("utf-8")
            raise HTTPException(status_code=422, detail=f"LaTeX Compilation Failed:\n{error_log}")
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Tectonic is not installed on the server.")

    @staticmethod
    def to_markdown(input_path: Path, output_dir: Path) -> Path:
        """
        Converts LaTeX to Markdown using Pandoc.
        """
        import pypandoc
        
        output_path = output_dir / "output.md"
        
        try:
            # pypandoc wrapper for: pandoc input.tex -f latex -t markdown -o output.md
            pypandoc.convert_file(
                str(input_path),
                'markdown',
                outputfile=str(output_path),
                format='latex'
            )
            return output_path
            
        except OSError:
            raise HTTPException(status_code=500, detail="Pandoc is not installed on the server.")
        except RuntimeError as e:
            raise HTTPException(status_code=422, detail=f"Pandoc Conversion Failed:\n{str(e)}")

def cleanup_temp_dir(path: str):
    """Background task to remove temporary files after response is sent."""
    shutil.rmtree(path, ignore_errors=True)

@app.post("/convert/{target_format}")
async def convert_latex(
    target_format: ConversionFormat,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a .tex file and convert it to PDF or Markdown.
    """
    if not file.filename.endswith(".tex"):
        raise HTTPException(status_code=400, detail="Only .tex files are supported")

    # Create a unique temporary directory for this request
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)

    try:
        # 1. Save uploaded file
        input_path = LatexConverter._save_upload_file(file, temp_path)
        
        # 2. Convert based on strategy
        if target_format == ConversionFormat.PDF:
            result_path = LatexConverter.to_pdf(input_path, temp_path)
            media_type = "application/pdf"
            filename = "document.pdf"
        elif target_format == ConversionFormat.MARKDOWN:
            result_path = LatexConverter.to_markdown(input_path, temp_path)
            media_type = "text/markdown"
            filename = "document.md"
        
        # 3. Schedule cleanup
        background_tasks.add_task(cleanup_temp_dir, temp_dir)

        # 4. Return file
        return FileResponse(
            path=result_path,
            filename=filename,
            media_type=media_type
        )

    except Exception as e:
        # cleanup immediately on error since background task won't trigger
        cleanup_temp_dir(temp_dir)
        raise e
