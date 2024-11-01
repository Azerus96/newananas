# training/checkpoint.py

import os
import json
import torch
from datetime import datetime
from typing import Dict, Any

class CheckpointManager:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.checkpoints = []
        self._create_dirs()

    def _create_dirs(self):
        """Создает необходимые директории"""
        os.makedirs(self.base_dir, exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'models'), exist_ok=True)
        os.makedirs(os.path.join(self.base_dir, 'stats'), exist_ok=True)

    def save_checkpoint(self, 
                       agent: Any,
                       stats: Dict,
                       episode: int,
                       metadata: Dict = None):
        """Сохраняет чекпоинт"""
        timestamp = # training/checkpoint.py (продолжение)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        checkpoint_dir = os.path.join(self.base_dir, f'checkpoint_{timestamp}')
        os.makedirs(checkpoint_dir, exist_ok=True)

        # Сохраняем модель
        model_path = os.path.join(checkpoint_dir, 'model.pt')
        torch.save({
            'episode': episode,
            'model_state_dict': agent.model.state_dict(),
            'optimizer_state_dict': agent.optimizer.state_dict(),
            'experience_buffer': agent.experience_buffer.get_state(),
        }, model_path)

        # Сохраняем статистику
        stats_path = os.path.join(checkpoint_dir, 'stats.json')
        with open(stats_path, 'w') as f:
            json.dump({
                'episode': episode,
                'timestamp': timestamp,
                'stats': stats,
                'metadata': metadata or {}
            }, f, indent=4)

        self.checkpoints.append({
            'path': checkpoint_dir,
            'episode': episode,
            'timestamp': timestamp
        })

    def load_checkpoint(self, checkpoint_id: str = 'latest') -> Dict:
        """Загружает чекпоинт"""
        if checkpoint_id == 'latest':
            if not self.checkpoints:
                raise ValueError("No checkpoints available")
            checkpoint_dir = max(self.checkpoints, key=lambda x: x['timestamp'])['path']
        else:
            checkpoint_dir = os.path.join(self.base_dir, checkpoint_id)

        if not os.path.exists(checkpoint_dir):
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        # Загружаем модель
        model_path = os.path.join(checkpoint_dir, 'model.pt')
        model_state = torch.load(model_path)

        # Загружаем статистику
        stats_path = os.path.join(checkpoint_dir, 'stats.json')
        with open(stats_path, 'r') as f:
            stats = json.load(f)

        return {
            'model_state': model_state,
            'stats': stats
        }

    def get_checkpoint_list(self) -> List[Dict]:
        """Возвращает список доступных чекпоинтов"""
        return sorted(self.checkpoints, key=lambda x: x['timestamp'])

    def cleanup_old_checkpoints(self, max_checkpoints: int = 5):
        """Удаляет старые чекпоинты, оставляя только последние max_checkpoints"""
        if len(self.checkpoints) <= max_checkpoints:
            return

        checkpoints_to_remove = sorted(
            self.checkpoints,
            key=lambda x: x['timestamp']
        )[:-max_checkpoints]

        for checkpoint in checkpoints_to_remove:
            checkpoint_dir = checkpoint['path']
            if os.path.exists(checkpoint_dir):
                shutil.rmtree(checkpoint_dir)
            self.checkpoints.remove(checkpoint)
