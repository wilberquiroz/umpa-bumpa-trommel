import pygame
import time
import numpy as np


class LoopManager:
    def __init__(self, expected_events, window):
        """
        expected_events: lista de segundos en los que el usuario debe hacer eventos.
        window: tamaño de la ventana móvil.
        """
        self.expected = np.array(expected_events)
        self.window = window

        # Tiempo absoluto desde inicio de round
        self.start_time = time.perf_counter()

        # Registro de inputs del usuario
        self.user_inputs = []

        # Progreso actual (índice del próximo objetivo)
        self.current_index = 0

        self.current_state = 0 #Beat Mode

        self.current_notes = []
        self.expected_notes = np.array([63,49,51])

    def set_expected(self, expected):
        self.expected = np.array(expected)
    
    def set_melodie_mode(self):
        self.current_state = 1 #Melodie

    def reset(self):
        self.start_time = time.perf_counter()
        self.user_inputs = []
        self.current_notes = []
        self.current_index = 0

    def register_input(self, note=0):
        """Se llama cuando el usuario presiona la tecla adecuada."""
        now = time.perf_counter() - self.start_time
        #print(now)
        if self.current_state == 1:
            self.current_notes.append((now,note))
        else:
            self.user_inputs.append(now)


    def update(self):
        """
        Llamado en cada frame.
        Devuelve:
            'progress'     si avanzó un evento,
            'reset'        si debe reiniciarse todo,
            None           si no pasó nada importante.
        """
        now = time.perf_counter()
        elapsed = now - self.start_time

        # Si excedió la ventana total → reset
        if elapsed > self.window:
            self.reset()
            return 'reset'

        
        return self._compare_vectors(self.user_inputs)

        # Validar si el usuario hizo el evento correcto
        #if self.current_index < len(self.expected):
        #    target = self.expected[self.current_index]

            # Checar inputs para saber si alguno cae dentro de tolerancia
            #for inp in self.user_inputs:
              
                #tolerance = target * 0.3
            #    tolerance = 0.2
            #    if (target - tolerance) <= inp <= (target + tolerance):
                    # Acierto
            #        self.current_index += 1
            #        return 'progress'

        #return None

    def _equal_rotated(self, a, b):   
        if len(a) != len(b):
            return False

        for shift in range(len(a)):
            if np.array_equal(np.roll(a, shift), b):
                return True
        
        return False
    
    def _compare_vectors(self, tolerance=0.2):
        """
        reference: vector de referencia, ej. [0, 0.937, 1.875, 2.812]
        received: vector a comparar
        tolerance: margen para coincidencia

        Retorna:
            "next"     → todas coinciden
            "progress" → al menos una coincide
            "trampa"   → Hizo mas de los permitidos
            "none"     → ninguna coincide
        """
        toleranz = 0
        received = None
        if self.current_state == 1:
            toleranz = 0.01
            #print(self.current_notes)
            received = np.array([t[0] for t in self.current_notes])
        else: 
            toleranz = 0.12
            received = np.array(self.user_inputs)

        reference = self.expected
        size = len(reference)
        
        if len(received) < 2:
            return None
        
        if len(received) > size and self.current_state == 0:
            #print(self.current_state)
            return "trampa"
        
        # Distancias consecutivas
        ref_dist = np.diff(reference)
        rec_dist = np.diff(received)

        compara = None
        if len(rec_dist) < len(ref_dist):
            rec_dist = np.concatenate([rec_dist, np.full(len(ref_dist) - len(rec_dist), 0)])

        
        try:
            comp_vec = np.abs(ref_dist - rec_dist)
            eval = comp_vec < toleranz
        except:
            #print(rec_dist)
            eval = [False]
            compara = 'rapido'
        
        if self.current_state == 1:
            print(rec_dist[0], ref_dist[0])
            if rec_dist[0] < ref_dist[0] - toleranz:
                compara =  "rapido"
            elif rec_dist[0] > ref_dist[0] + toleranz:
                compara = "lento"
            else:
                compara = None
        
        if np.all(eval):
            if self.current_state == 0:
                return "next"
            #else: 
                
        elif np.any(eval):
            if self.current_state == 0:
                return "progress"
            else:
                print("To end", rec_dist[10])
                if rec_dist[10] != 0:
                    notes = np.array([t[1] for t in self.current_notes])
                    #print(notes)
                    if np.all(np.isin(notes, self.expected_notes)):
                        return "end"
                    else:
                        return "fnotes"
        else:
            if self.current_state == 1: 
                if compara:
                    return compara
                    
            return None

