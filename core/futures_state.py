import asyncio

class FuturesStateManager:
    """
    Gerenciador thread-safe assíncrono para as posições ativas de futuros.
    Evita race conditions entre WebSocket, Bot Loop e Trailing Lock.
    """
    def __init__(self):
        self._positions = {}
        self._lock = asyncio.Lock()
        
    def get_all_sync(self):
        """Retorna as posições sincronamente (para dashboards e UI)."""
        return dict(self._positions)
        
    async def get_all(self):
        """Retorna uma cópia do dicionário de posições ativas."""
        async with self._lock:
            return dict(self._positions)
            
    async def get(self, symbol):
        """Retorna a cópia (ou referência, mas em leitura) da posição."""
        async with self._lock:
            # Retorna shallow copy para evitar modificações acidentais sem update()
            pos = self._positions.get(symbol)
            return dict(pos) if pos else None
            
    async def add(self, symbol, data):
        """Adiciona ou substitui uma posição."""
        async with self._lock:
            self._positions[symbol] = data
            
    async def remove(self, symbol):
        """Remove a posição de um símbolo, se existir, e a retorna."""
        async with self._lock:
            return self._positions.pop(symbol, None)
            
    async def update(self, symbol, key, value):
        """Atualiza um campo específico de uma posição existente."""
        async with self._lock:
            if symbol in self._positions:
                self._positions[symbol][key] = value
                
    async def has_symbol(self, symbol):
        """Verifica se o símbolo está nas posições ativas."""
        async with self._lock:
            return symbol in self._positions
            
    async def count(self):
        """Retorna a quantidade de posições ativas."""
        async with self._lock:
            return len(self._positions)

# Instância Singleton Global
futures_state = FuturesStateManager()
