-- 0005: Seed Colombian national holidays for 2027
-- REQ-RD-003 — Populated from official Colombian holiday calendar
-- Easter 2027 = March 28; movable holidays follow Ley Emiliani (next Monday rule)
-- Update this file annually or when law changes.

INSERT INTO holidays (date, name) VALUES
  ('2027-01-01', 'Año Nuevo'),
  ('2027-01-11', 'Reyes Magos'),
  ('2027-03-22', 'San José'),
  ('2027-03-25', 'Jueves Santo'),
  ('2027-03-26', 'Viernes Santo'),
  ('2027-05-01', 'Día del Trabajo'),
  ('2027-05-10', 'Ascensión del Señor'),
  ('2027-05-31', 'Corpus Christi'),
  ('2027-06-07', 'Sagrado Corazón de Jesús'),
  ('2027-07-05', 'San Pedro y San Pablo'),
  ('2027-07-20', 'Día de la Independencia'),
  ('2027-08-07', 'Batalla de Boyacá'),
  ('2027-08-16', 'Asunción de la Virgen'),
  ('2027-10-18', 'Día de la Raza'),
  ('2027-11-01', 'Todos los Santos'),
  ('2027-11-15', 'Independencia de Cartagena'),
  ('2027-12-08', 'Inmaculada Concepción'),
  ('2027-12-25', 'Navidad')
ON CONFLICT (date) DO NOTHING;
