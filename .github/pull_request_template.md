## Qué cambia y por qué

<!-- Una o dos frases para quien usa la app y, si aplica, el ID de docs/PENDIENTE.md -->

## Versión

- [ ] `pyproject.toml` y `src/partes_salida/__init__.py` con la misma versión (o «sin versión: no se publica»)
- [ ] Entrada en `CHANGELOG.md`

## Pruebas

- [ ] `scripts/qa.sh todo` en verde
- [ ] Test nuevo o ajustado; comprobado que **falla al revertir** el cambio
- [ ] Si toca `parte.py` o `impresion.py`: parte de prueba impreso en la bandeja A6

## Datos personales (repositorio público)

- [ ] Ningún Excel, ZIP, foto ni dato real en el diff (`git diff --name-only main`)
- [ ] Si se lee una columna nueva del Excel: ADR en `docs/DECISIONES.md` y `docs/SEGURIDAD_Y_DATOS.md`
- [ ] Contraseñas solo en el llavero

## Impacto documental

<!-- ESPECIFICACION, ARQUITECTURA, DESIGN, SEGURIDAD_Y_DATOS, OPERACIONES, ESPECIFICACION_QR… o «sin impacto documental» -->

## Capturas

<!-- Si cambia una pantalla: `make capturas` y las afectadas de docs/capturas/ -->
