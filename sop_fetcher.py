#!/usr/bin/env python3
"""
SOP Fetcher - Handles fetching and tracking SOPs from directory
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
import hashlib
from typing import Dict, List, Tuple
import chromadb
from sentence_transformers import SentenceTransformer
import docx
import PyPDF2
import io

class SOPFetcher:
    def __init__(self, sop_directory: str = "/Users/roshandhakal/Desktop/AD/sopchatbot/SOPs"):
        self.sop_directory = Path(sop_directory)
        self.metadata_file = Path("sop_metadata.json")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.chroma_client.get_or_create_collection("sop_documents")
        
    def load_metadata(self) -> Dict:
        """Load existing metadata about SOPs"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {
            "last_fetch": None,
            "files": {},
            "fetch_history": []
        }
    
    def save_metadata(self, metadata: Dict):
        """Save metadata about SOPs"""
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def get_file_hash(self, filepath: Path) -> str:
        """Get MD5 hash of file content"""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def get_file_modified_time(self, filepath: Path) -> float:
        """Get file modification time"""
        return os.path.getmtime(filepath)
    
    def extract_text_from_file(self, filepath: Path) -> str:
        """Extract text content from various file types"""
        try:
            if filepath.suffix.lower() == '.pdf':
                with open(filepath, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    return text
            
            elif filepath.suffix.lower() in ['.docx', '.doc']:
                doc = docx.Document(str(filepath))
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            
            elif filepath.suffix.lower() in ['.txt', '.md']:
                with open(filepath, 'r', encoding='utf-8') as file:
                    return file.read()
            
            else:
                return f"Unsupported file type: {filepath.suffix}"
                
        except Exception as e:
            return f"Error reading file {filepath.name}: {str(e)}"
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks
    
    def analyze_directory(self) -> Tuple[List[Path], List[Path], List[Path]]:
        """Analyze directory for new, modified, and deleted files"""
        metadata = self.load_metadata()
        current_files = {}
        new_files = []
        modified_files = []
        
        # Scan all files in directory
        supported_extensions = ['.pdf', '.docx', '.doc', '.txt', '.md']
        for filepath in self.sop_directory.rglob('*'):
            if filepath.is_file() and filepath.suffix.lower() in supported_extensions:
                relative_path = str(filepath.relative_to(self.sop_directory))
                file_hash = self.get_file_hash(filepath)
                modified_time = self.get_file_modified_time(filepath)
                
                current_files[relative_path] = {
                    "hash": file_hash,
                    "modified": modified_time,
                    "size": filepath.stat().st_size
                }
                
                # Check if file is new or modified
                if relative_path not in metadata["files"]:
                    new_files.append(filepath)
                elif metadata["files"][relative_path]["hash"] != file_hash:
                    modified_files.append(filepath)
        
        # Check for deleted files
        deleted_files = []
        for old_file in metadata["files"]:
            if old_file not in current_files:
                deleted_files.append(old_file)
        
        return new_files, modified_files, deleted_files
    
    def fetch_and_index_sops(self, progress_callback=None) -> Dict:
        """Fetch all SOPs and index them in ChromaDB"""
        new_files, modified_files, deleted_files = self.analyze_directory()
        
        total_files = len(new_files) + len(modified_files)
        processed = 0
        
        results = {
            "new_count": len(new_files),
            "modified_count": len(modified_files),
            "deleted_count": len(deleted_files),
            "total_processed": 0,
            "errors": []
        }
        
        # Process new files
        for filepath in new_files:
            try:
                if progress_callback:
                    progress_callback(processed / total_files, f"Processing new file: {filepath.name}")
                
                text = self.extract_text_from_file(filepath)
                if text and not text.startswith("Error") and not text.startswith("Unsupported"):
                    chunks = self.chunk_text(text)
                    
                    # Add to ChromaDB
                    for i, chunk in enumerate(chunks):
                        chunk_id = f"{filepath.stem}_{i}"
                        embedding = self.embedding_model.encode(chunk)
                        
                        self.collection.add(
                            embeddings=[embedding.tolist()],
                            documents=[chunk],
                            metadatas=[{
                                "source": filepath.name,
                                "chunk_index": i,
                                "total_chunks": len(chunks),
                                "file_path": str(filepath.relative_to(self.sop_directory)),
                                "indexed_at": datetime.now().isoformat()
                            }],
                            ids=[chunk_id]
                        )
                
                processed += 1
                results["total_processed"] += 1
                
            except Exception as e:
                results["errors"].append(f"Error processing {filepath.name}: {str(e)}")
        
        # Process modified files
        for filepath in modified_files:
            try:
                if progress_callback:
                    progress_callback(processed / total_files, f"Processing modified file: {filepath.name}")
                
                # Delete old chunks
                file_chunks = self.collection.get(
                    where={"source": filepath.name}
                )
                if file_chunks['ids']:
                    self.collection.delete(ids=file_chunks['ids'])
                
                # Add new chunks
                text = self.extract_text_from_file(filepath)
                if text and not text.startswith("Error") and not text.startswith("Unsupported"):
                    chunks = self.chunk_text(text)
                    
                    for i, chunk in enumerate(chunks):
                        chunk_id = f"{filepath.stem}_{i}"
                        embedding = self.embedding_model.encode(chunk)
                        
                        self.collection.add(
                            embeddings=[embedding.tolist()],
                            documents=[chunk],
                            metadatas=[{
                                "source": filepath.name,
                                "chunk_index": i,
                                "total_chunks": len(chunks),
                                "file_path": str(filepath.relative_to(self.sop_directory)),
                                "indexed_at": datetime.now().isoformat()
                            }],
                            ids=[chunk_id]
                        )
                
                processed += 1
                results["total_processed"] += 1
                
            except Exception as e:
                results["errors"].append(f"Error processing {filepath.name}: {str(e)}")
        
        # Handle deleted files
        for deleted_file in deleted_files:
            try:
                file_chunks = self.collection.get(
                    where={"file_path": deleted_file}
                )
                if file_chunks['ids']:
                    self.collection.delete(ids=file_chunks['ids'])
            except Exception as e:
                results["errors"].append(f"Error removing {deleted_file}: {str(e)}")
        
        # Update metadata
        metadata = self.load_metadata()
        
        # Update file information
        current_files = {}
        for filepath in self.sop_directory.rglob('*'):
            if filepath.is_file() and filepath.suffix.lower() in ['.pdf', '.docx', '.doc', '.txt', '.md']:
                relative_path = str(filepath.relative_to(self.sop_directory))
                current_files[relative_path] = {
                    "hash": self.get_file_hash(filepath),
                    "modified": self.get_file_modified_time(filepath),
                    "size": filepath.stat().st_size
                }
        
        # Add to fetch history
        fetch_record = {
            "timestamp": datetime.now().isoformat(),
            "new_files": len(new_files),
            "modified_files": len(modified_files),
            "deleted_files": len(deleted_files),
            "total_files": len(current_files)
        }
        
        metadata["files"] = current_files
        metadata["last_fetch"] = datetime.now().isoformat()
        metadata["fetch_history"].append(fetch_record)
        
        # Keep only last 10 fetch records
        if len(metadata["fetch_history"]) > 10:
            metadata["fetch_history"] = metadata["fetch_history"][-10:]
        
        self.save_metadata(metadata)
        
        if progress_callback:
            progress_callback(1.0, "Completed!")
        
        return results
    
    def get_fetch_status(self) -> Dict:
        """Get current fetch status"""
        metadata = self.load_metadata()
        
        if not metadata["last_fetch"]:
            return {
                "last_fetch": None,
                "last_fetch_formatted": "Never",
                "total_files": 0,
                "needs_update": True
            }
        
        last_fetch = datetime.fromisoformat(metadata["last_fetch"])
        now = datetime.now()
        time_diff = now - last_fetch
        
        # Format time difference
        if time_diff.days > 0:
            time_ago = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif time_diff.seconds > 60:
            minutes = time_diff.seconds // 60
            time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            time_ago = "Just now"
        
        # Check if any files have been modified since last fetch
        needs_update = False
        if metadata["files"]:
            for file_path, file_info in metadata["files"].items():
                full_path = self.sop_directory / file_path
                if full_path.exists():
                    current_modified = self.get_file_modified_time(full_path)
                    if current_modified > file_info["modified"]:
                        needs_update = True
                        break
        
        return {
            "last_fetch": metadata["last_fetch"],
            "last_fetch_formatted": time_ago,
            "total_files": len(metadata["files"]),
            "needs_update": needs_update,
            "fetch_history": metadata.get("fetch_history", [])
        }