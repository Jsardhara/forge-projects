'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import 'leaflet/dist/leaflet.css';
import clusters from '../data/clusters.json';

const MapContainer = dynamic(() => import('react-leaflet').then((m) => m.MapContainer), { ssr: false });
const TileLayer = dynamic(() => import('react-leaflet').then((m) => m.TileLayer), { ssr: false });
const CircleMarker = dynamic(() => import('react-leaflet').then((m) => m.CircleMarker), { ssr: false });
const Popup = dynamic(() => import('react-leaflet').then((m) => m.Popup), { ssr: false });

const COLORS: Record<string, string> = {
  confirmed: '#b3441a',
  suspected: '#d97706',
  monitoring: '#3d5a3a',
};

export default function ClusterMap() {
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  if (!ready) {
    return (
      <div className="h-[480px] flex items-center justify-center bg-ink/5 rounded-lg">
        <span className="text-ink/50">Loading map…</span>
      </div>
    );
  }

  return (
    <div className="h-[480px] rounded-lg overflow-hidden border border-ink/10">
      <MapContainer center={[15, -10]} zoom={3} scrollWheelZoom={false} style={{ height: '100%' }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {clusters.map((c) => {
          const radius = c.status === 'confirmed' ? 14 : c.status === 'suspected' ? 10 : 8;
          return (
            <CircleMarker
              key={c.id}
              center={[c.lat, c.lng]}
              radius={radius}
              pathOptions={{
                color: COLORS[c.status],
                fillColor: COLORS[c.status],
                fillOpacity: 0.55,
                weight: 2,
              }}
            >
              <Popup>
                <div className="text-sm max-w-xs">
                  <strong>{c.location}</strong>
                  <div className="text-xs uppercase tracking-wide my-1" style={{ color: COLORS[c.status] }}>
                    {c.status} · {c.cases} confirmed · {c.suspected} suspected
                  </div>
                  <p className="my-2">{c.note}</p>
                  <a href={c.source_url} target="_blank" rel="noopener noreferrer">
                    {c.source_label} ↗
                  </a>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
