# Sistema experto simple para sumar y restar

# Base de conocimiento: reglas del sistema
def regla_suma(a, b):
    return a + b

def regla_resta(a, b):
    return a - b

# Motor de inferencia: analiza los datos y aplica la regla adecuada
def motor_inferencia(operacion, num1, num2):
    if operacion.lower() == "sumar":
        return f"Resultado: {regla_suma(num1, num2)}"
    elif operacion.lower() == "restar":
        return f"Resultado: {regla_resta(num1, num2)}"
    else:
        return "Operación no reconocida. Por favor ingresa 'sumar' o 'restar'."

# Módulo de explicación: muestra cómo llegó al resultado
def explicacion(operacion, num1, num2):
    if operacion.lower() == "sumar":
        return f"Se sumaron {num1} y {num2} aplicando la regla: SI operación es 'sumar' ENTONCES resultado = num1 + num2."
    elif operacion.lower() == "restar":
        return f"Se restó {num2} a {num1} aplicando la regla: SI operación es 'restar' ENTONCES resultado = num1 - num2."
    else:
        return "No se pudo generar explicación debido a una operación desconocida."

# Interfaz simple para el usuario
def interfaz_usuario():
    print("Bienvenido al Sistema Experto de Sumas y Restas")
    operacion = input("¿Qué operación deseas realizar? (sumar/restar): ")
    
    try:
        num1 = float(input("Ingresa el primer número: "))
        num2 = float(input("Ingresa el segundo número: "))
    except ValueError:
        print("Error: Debes ingresar valores numéricos válidos.")
        return
    
    # Procesar la información
    resultado = motor_inferencia(operacion, num1, num2)
    razonamiento = explicacion(operacion, num1, num2)
    
    # Mostrar resultados
    print("\n--- Resultado ---")
    print(resultado)
    print("\n--- Explicación ---")
    print(razonamiento)

# Ejecutar el sistema experto
if __name__ == "__main__":
    interfaz_usuario()
