#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor de enlaces directos de eventos deportivos de tvtvhd.com
Extrae enlaces de streaming de partidos y eventos deportivos
"""

import requests
import re
import json
import base64
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import time
from datetime import datetime

class EventExtractor:
    def __init__(self):
        self.base_url = "https://tvtvhd.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-AR,es;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
    def get_page_content(self, url):
        """Obtener contenido de página"""
        try:
            print(f"📡 Accediendo: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"❌ Error accediendo a {url}: {e}")
            return None
    
    def get_json_data(self):
        """Obtener datos del endpoint status.json"""
        try:
            url = f"{self.base_url}/status.json"
            print(f"📡 Obteniendo datos JSON: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ Error obteniendo JSON: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Error parseando JSON: {e}")
            return None
    
    def extract_channels_from_json(self):
        """Extraer canales del JSON"""
        data = self.get_json_data()
        if not data:
            return []
        
        channels = []
        
        for country, channel_list in data.items():
            print(f"🌍 {country}: {len(channel_list)} canales")
            
            for channel in channel_list:
                name = channel.get('Canal', '')
                status = channel.get('Estado', '')
                link = channel.get('Link', '')
                
                if name and link:
                    channels.append({
                        'name': f"{name} ({country})",
                        'url': link,
                        'status': status,
                        'country': country,
                        'type': 'channel'
                    })
        
        print(f"📺 Total canales encontrados: {len(channels)}")
        return channels
    
    def get_events_json(self):
        """Obtener eventos del JSON de agenda"""
        try:
            url = "https://pltvhd.com/diaries.json"
            print(f"📡 Obteniendo eventos JSON: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"❌ Error obteniendo eventos JSON: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Error parseando eventos JSON: {e}")
            return None
    
    def decode_base64_url(self, encoded_url):
        """Decodificar URL base64"""
        try:
            # Extraer la parte después de 'r='
            if 'r=' in encoded_url:
                encoded = encoded_url.split('r=')[1]
                decoded = base64.b64decode(encoded).decode('utf-8')
                return decoded
            return encoded_url
        except Exception as e:
            print(f"❌ Error decodificando URL: {e}")
            return None
    
    def extract_events_from_agenda(self):
        """Extraer eventos de la agenda con todos sus enlaces"""
        data = self.get_events_json()
        if not data or 'data' not in data:
            return []
        
        events = []
        
        for event_data in data['data']:
            attrs = event_data.get('attributes', {})
            
            description = attrs.get('diary_description', '')
            hour = attrs.get('diary_hour', '')
            date = attrs.get('date_diary', '')
            country = attrs.get('country', {}).get('data', {}).get('attributes', {}).get('name', '')
            
            embeds = attrs.get('embeds', {}).get('data', [])
            
            if embeds:
                event = {
                    'description': description,
                    'hour': hour,
                    'date': date,
                    'country': country,
                    'embeds': [],
                    'type': 'event'
                }
                
                for embed in embeds:
                    embed_attrs = embed.get('attributes', {})
                    embed_name = embed_attrs.get('embed_name', '')
                    embed_iframe = embed_attrs.get('embed_iframe', '')
                    
                    # Decodificar URL base64
                    decoded_url = self.decode_base64_url(embed_iframe)
                    
                    if decoded_url:
                        # Construir URL completa
                        full_url = urljoin(self.base_url, decoded_url)
                        
                        event['embeds'].append({
                            'name': embed_name,
                            'url': full_url,
                            'original_iframe': embed_iframe
                        })
                
                if event['embeds']:
                    events.append(event)
        
        print(f"📅 Total eventos encontrados: {len(events)}")
        return events
    
    def extract_stream_from_event_page(self, event_url):
        """Extraer stream directo de página de evento"""
        content = self.get_page_content(event_url)
        if not content:
            return None
        
        # Patrones comunes de streams
        stream_patterns = [
            r'https?://[^"\'\s]+\.m3u8[^"\'\s]*',
            r'https?://[^"\'\s]+\.mpd[^"\'\s]*',
            r'source:\s*[\'"]([^\'"]+)[\'"]',
            r'file:\s*[\'"]([^\'"]+)[\'"]',
            r'url:\s*[\'"]([^\'"]+)[\'"]',
            r'playbackURL\s*=\s*[\'"]([^\'"]+)[\'"]',
            r'var\s+playbackURL\s*=\s*[\'"]([^\'"]+)[\'"]',
            r'data-src=[\'"]([^\'"]+)[\'"]',
            r'src=[\'"]([^\'"]+\.(?:m3u8|mpd)[^\'"]*)[\'"]',
        ]
        
        streams = []
        
        for pattern in stream_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1]
                
                if match and match.startswith('http'):
                    streams.append(match)
        
        # Buscar enlaces a páginas de streaming
        iframe_patterns = [
            r'<iframe[^>]+src=[\'"]([^\'"]+)[\'"]',
            r'<embed[^>]+src=[\'"]([^\'"]+)[\'"]',
        ]
        
        for pattern in iframe_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if match and not match.startswith('http'):
                    match = urljoin(self.base_url, match)
                
                # Extraer stream de la página del iframe
                if match and 'tvtvhd.com' in match:
                    iframe_stream = self.extract_stream_from_event_page(match)
                    if iframe_stream:
                        streams.extend(iframe_stream)
        
        # Eliminar duplicados y limpiar
        unique_streams = list(set(streams))
        clean_streams = [s for s in unique_streams if '.m3u8' in s or '.mpd' in s]
        
        return clean_streams
    
    
    def process_all_events(self):
        """Procesar todos los canales y eventos con sus enlaces"""
        print("🚀 Iniciando extracción de canales y eventos deportivos")
        print("=" * 60)
        
        all_streams = []
        
        # Extraer eventos de la agenda
        print("\n📅 Extrayendo eventos de la agenda...")
        events = self.extract_events_from_agenda()
        
        if events:
            print(f"\n🎯 Procesando {len(events)} eventos...")
            for i, event in enumerate(events, 1):
                print(f"\n⚽ [{i}/{len(events)}] {event['description']}")
                print(f"   🕐 {event['hour']} | 🌍 {event['country']}")
                
                # Procesar cada embed del evento
                for embed in event['embeds']:
                    print(f"   📺 {embed['name']}")
                    
                    streams = self.extract_stream_from_event_page(embed['url'])
                    
                    if streams:
                        for stream in streams:
                            all_streams.append({
                                'title': f"{event['description']} - {embed['name']}",
                                'url': stream,
                                'type': 'event',
                                'source': embed['url'],
                                'country': event['country'],
                                'event_description': event['description'],
                                'event_hour': event['hour'],
                                'event_date': event['date'],
                                'embed_name': embed['name']
                            })
                            print(f"     ✅ Stream: {stream[:80]}...")
                    else:
                        print(f"     ❌ No se encontraron streams")
                    
                    time.sleep(0.3)
        
        # Extraer canales del JSON
        print("\n📺 Extrayendo canales...")
        channels = self.extract_channels_from_json()
        
        if channels:
            # Filtrar solo canales activos
            active_channels = [c for c in channels if c['status'] == 'Activo']
            print(f"\n📺 Canales activos: {len(active_channels)}/{len(channels)}")
            
            # Procesar canales activos
            for i, channel in enumerate(active_channels, 1):
                print(f"\n📡 [{i}/{len(active_channels)}] {channel['name']}")
                
                streams = self.extract_stream_from_event_page(channel['url'])
                
                if streams:
                    for stream in streams:
                        all_streams.append({
                            'title': channel['name'],
                            'url': stream,
                            'type': 'channel',
                            'source': channel['url'],
                            'country': channel['country'],
                            'status': channel['status']
                        })
                        print(f"  ✅ Stream: {stream[:80]}...")
                else:
                    print(f"  ❌ No se encontraron streams")
                
                time.sleep(0.3)
        
        return all_streams
    
    def save_streams_m3u(self, streams, filename="canales_y_eventos.m3u"):
        """Guardar streams en formato M3U"""
        content = "#EXTM3U\n"
        
        for stream in streams:
            # Limpiar título
            title = re.sub(r'[^\w\s\-\.]', '', stream['title'])
            title = title.strip()
            
            # Determinar grupo basado en tipo y país
            stream_type = stream.get('type', 'channel')
            country = stream.get('country', 'General')
            
            if stream_type == 'event':
                group = f"Eventos {country}"
                # Agregar hora al título si es evento
                hour = stream.get('event_hour', '')
                if hour:
                    title = f"{title} [{hour}]"
            else:
                group = f"Canales {country}"
            
            # Extraer calidad si está en el URL
            quality = ""
            if "720p" in stream['url'].lower():
                quality = " (720p)"
            elif "1080p" in stream['url'].lower():
                quality = " (1080p)"
            
            # Crear línea EXTINF
            extinf = f'#EXTINF:-1 group-title="{group}",{title}{quality}'
            
            content += f"{extinf}\n{stream['url']}\n"
        
        # Agregar metadata
        content += f"\n# Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"# Total streams: {len(streams)}\n"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"\n💾 Guardado en: {filename}")
            return True
        except Exception as e:
            print(f"❌ Error guardando: {e}")
            return False
    
    def save_streams_json(self, streams, filename="deportes y eventos.json"):
        """Guardar streams en formato JSON"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(streams, f, ensure_ascii=False, indent=2)
            print(f"📄 JSON guardado en: {filename}")
            return True
        except Exception as e:
            print(f"❌ Error guardando JSON: {e}")
            return False
    
    def run(self):
        """Ejecutar proceso completo"""
        try:
            streams = self.process_all_events()
            
            if streams:
                print(f"\n✨ Proceso completado!")
                print(f"📊 Total streams encontrados: {len(streams)}")
                
                # Guardar en ambos formatos
                self.save_streams_m3u(streams)
                self.save_streams_json(streams)
                
                # Mostrar resumen
                print(f"\n📋 Resumen:")
                eventos = [s for s in streams if s['type'] == 'event']
                canales = [s for s in streams if s['type'] == 'channel']
                print(f"   ⚽ Eventos: {len(eventos)}")
                print(f"   📺 Canales: {len(canales)}")
                
                # Resumen por país
                print(f"\n📋 Resumen por país:")
                countries = {}
                for stream in streams:
                    country = stream.get('country', 'General')
                    countries[country] = countries.get(country, 0) + 1
                
                for country, count in sorted(countries.items()):
                    print(f"   🌍 {country}: {count}")
                
                return streams
            else:
                print("❌ No se encontraron streams")
                return []
                
        except Exception as e:
            print(f"❌ Error en proceso: {e}")
            return []

def main():
    """Función principal"""
    extractor = EventExtractor()
    extractor.run()

if __name__ == "__main__":
    main()
