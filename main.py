import shutil
import subprocess
import tempfile
import os
import re
from enum import Enum
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse

app = FastAPI(title="LaTeX Conversion API")

class ConversionFormat(str, Enum):
    PDF = "pdf"
    MARKDOWN = "markdown"

def sanitize_filename(name: str) -> str:
    """
    Security: Removes directory traversals (../) and unsafe characters.
    Allows: A-Z, a-z, 0-9, -, _, ., and spaces.
    """
    # Get just the filename (removes any directory paths like /tmp/)
    name = os.path.basename(name)
    # Remove characters that aren't alphanumeric, spaces, dots, dashes, or underscores
    name = re.sub(r'[^a-zA-Z0-9_\-\. ]', '', name)
    # Fallback if the name becomes empty after sanitization
    if not name:
        return "document"
    return name

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
        """
        try:
            cmd = [
                "tectonic",
                str(input_path),
                "--outdir",
                str(output_dir),
                "--print", 
                "--keep-intermediates"
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return output_dir / "input.pdf"
        
        except subprocess.CalledProcessError as e:
            error_log = e.stderr.decode("utf-8")
            raise HTTPException(status_code=422, detail=f"LaTeX Compilation Failed:\n{error_log}")
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Tectonic is not installed on the server.")

    @staticmethod
    def to_markdown(input_path: Path, output_dir: Path) -> Path:
        """
        Converts LaTeX to Markdown using Pandoc (GitHub Flavored Markdown).
        """
        import pypandoc
        
        output_path = output_dir / "output.md"
        
        try:
            pypandoc.convert_file(
                str(input_path),
                'gfm',  # GitHub Flavored Markdown for better table support
                outputfile=str(output_path),
                format='latex',
                extra_args=['--wrap=none']
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
    file: UploadFile = File(...),
    output_filename: Optional[str] = Query(
        None, 
        description="Optional custom filename (without extension). e.g. 'My_Report'"
    )
):
    """
    Upload a .tex file and convert it to PDF or Markdown.
    If 'output_filename' is not provided, defaults to the original filename.
    """
    if not file.filename.endswith(".tex"):
        raise HTTPException(status_code=400, detail="Only .tex files are supported")

    # 1. Determine Output Filename
    if output_filename:
        base_name = sanitize_filename(output_filename)
    else:
        # Use original filename (e.g. "thesis.tex" -> "thesis")
        base_name = Path(file.filename).stem

    # Create a unique temporary directory for this request
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)

    try:
        # 2. Save uploaded file
        input_path = LatexConverter._save_upload_file(file, temp_path)
        
        # 3. Convert based on strategy
        if target_format == ConversionFormat.PDF:
            result_path = LatexConverter.to_pdf(input_path, temp_path)
            media_type = "application/pdf"
            download_name = f"{base_name}.pdf"
            
        elif target_format == ConversionFormat.MARKDOWN:
            result_path = LatexConverter.to_markdown(input_path, temp_path)
            media_type = "text/markdown"
            download_name = f"{base_name}.md"
        
        # 4. Rename file to match requested name (so FileResponse finds it easily)
        final_path = temp_path / download_name
        result_path.rename(final_path)

        # 5. Schedule cleanup
        background_tasks.add_task(cleanup_temp_dir, temp_dir)

        # 6. Return file
        return FileResponse(
            path=final_path,
            filename=download_name,
            media_type=media_type
        )

    except Exception as e:
        # cleanup immediately on error since background task won't trigger
        cleanup_temp_dir(temp_dir)
        raise e
