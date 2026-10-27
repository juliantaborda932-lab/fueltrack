-- FuelTrack: modelo físico para Supabase (PostgreSQL). Ejecutar en SQL Editor de Supabase.
-- La app también crea estas tablas sola al iniciar (metadata.create_all).

CREATE TABLE estaciones (
	id_estacion SERIAL NOT NULL, 
	nombre VARCHAR(100) NOT NULL, 
	latitud FLOAT NOT NULL, 
	longitud FLOAT NOT NULL, 
	aliada BOOLEAN NOT NULL, 
	PRIMARY KEY (id_estacion)
);

CREATE TABLE usuarios (
	id_usuario SERIAL NOT NULL, 
	nombre VARCHAR(80) NOT NULL, 
	correo VARCHAR(120) NOT NULL, 
	contrasena_hash VARCHAR(60) NOT NULL, 
	acepta_politica BOOLEAN NOT NULL, 
	intentos_fallidos INTEGER NOT NULL, 
	bloqueado_hasta TIMESTAMP WITHOUT TIME ZONE, 
	fecha_registro TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id_usuario), 
	UNIQUE (correo)
);

CREATE TABLE precios (
	id_precio SERIAL NOT NULL, 
	id_estacion INTEGER NOT NULL, 
	tipo_combustible VARCHAR(15) NOT NULL, 
	precio_galon FLOAT NOT NULL, 
	fecha_actualizacion TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id_precio), 
	FOREIGN KEY(id_estacion) REFERENCES estaciones (id_estacion)
);

CREATE TABLE solicitudes_soporte (
	radicado VARCHAR(12) NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	categoria VARCHAR(30) NOT NULL, 
	descripcion TEXT NOT NULL, 
	estado VARCHAR(10) NOT NULL, 
	fecha TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (radicado), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario)
);

CREATE TABLE suscripciones (
	id_suscripcion SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	plan VARCHAR(10) NOT NULL, 
	estado VARCHAR(10) NOT NULL, 
	PRIMARY KEY (id_suscripcion), 
	UNIQUE (id_usuario), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario)
);

CREATE TABLE vehiculos (
	id_vehiculo SERIAL NOT NULL, 
	id_usuario INTEGER NOT NULL, 
	placa VARCHAR(6) NOT NULL, 
	marca VARCHAR(40) NOT NULL, 
	modelo VARCHAR(40) NOT NULL, 
	anio INTEGER NOT NULL, 
	tipo_combustible VARCHAR(15) NOT NULL, 
	km_mantenimiento INTEGER NOT NULL, 
	PRIMARY KEY (id_vehiculo), 
	FOREIGN KEY(id_usuario) REFERENCES usuarios (id_usuario), 
	UNIQUE (placa)
);

CREATE TABLE alertas (
	id_alerta SERIAL NOT NULL, 
	id_vehiculo INTEGER NOT NULL, 
	tipo VARCHAR(15) NOT NULL, 
	mensaje VARCHAR(200) NOT NULL, 
	fecha TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id_alerta), 
	FOREIGN KEY(id_vehiculo) REFERENCES vehiculos (id_vehiculo)
);

CREATE TABLE pagos (
	id_pago SERIAL NOT NULL, 
	id_suscripcion INTEGER NOT NULL, 
	referencia_pasarela VARCHAR(50) NOT NULL, 
	valor FLOAT NOT NULL, 
	estado VARCHAR(10) NOT NULL, 
	fecha TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id_pago), 
	FOREIGN KEY(id_suscripcion) REFERENCES suscripciones (id_suscripcion), 
	UNIQUE (referencia_pasarela)
);

CREATE TABLE tanqueos (
	id_tanqueo SERIAL NOT NULL, 
	id_vehiculo INTEGER NOT NULL, 
	id_estacion INTEGER, 
	fecha DATE NOT NULL, 
	galones FLOAT NOT NULL, 
	precio_galon FLOAT NOT NULL, 
	valor_total FLOAT NOT NULL, 
	kilometraje INTEGER NOT NULL, 
	rendimiento_km_gal FLOAT, 
	origen VARCHAR(6) NOT NULL, 
	PRIMARY KEY (id_tanqueo), 
	FOREIGN KEY(id_vehiculo) REFERENCES vehiculos (id_vehiculo), 
	FOREIGN KEY(id_estacion) REFERENCES estaciones (id_estacion)
);
