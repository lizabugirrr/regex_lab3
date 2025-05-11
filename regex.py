"""
This module implements a finite state machine (FSM) for regular expression matching.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List

class State(ABC):
    """
    Abstract base class for all states in the FSM.
    """
    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractmethod
    def check_self(self, char: str) -> bool:
        """
        function checks whether occured character is handled by current state
        """
        pass

    def check_next(self, next_char: str) -> State | Exception:
        """
        Check if the next character is handled by any of the next states.
        """
        for state in self.next_states:
            if state.check_self(next_char):
                return state
        raise NotImplementedError("rejected string")

class StartState(State):
    """
    Initial state of the FSM.
    """
    next_states: List[State] = []
    def __init__(self):
        self.next_states = []
    def check_self(self, char):
        return False

class TerminationState(State):
    """
    Final state of the FSM.
    """
    next_states: List[State] = []

    def __init__(self):
        self.next_states = []

    def check_self(self, char):
        return False

class DotState(State):
    """
    state for . character (any character accepted)
    """
    next_states: List[State] = []

    def __init__(self):
        self.next_states = []

    def check_self(self, char: str):
        return True

class AsciiState(State):
    """
    state for alphabet letters or numbers
    """
    next_states: List[State] = []
    curr_sym = ""

    def __init__(self, symbol: str) -> None:
        self.next_states = []
        self.curr_sym = symbol

    def check_self(self, curr_char: str) -> bool:
        return curr_char == self.curr_sym

class StarState(State):
    """
    state for * character (zero or more occurrences)
    """
    next_states: List[State] = []

    def __init__(self, checking_state: State):
        self.next_states = []
        self.checking_state = checking_state

    def check_self(self, char):
        if self.checking_state.check_self(char):
            return True
        for state in self.next_states:
            if state.check_self(char):
                return True
        return False

class PlusState(State):
    """
    state for + character (one or more occurrences)
    """
    next_states: List[State] = []

    def __init__(self, checking_state: State):
        self.next_states = []
        self.checking_state = checking_state
        self.matched_at_least_one = False

    def check_self(self, char):
        if self.checking_state.check_self(char):
            self.matched_at_least_one = True
            return True
        if self.matched_at_least_one:
            for state in self.next_states:
                if state.check_self(char):
                    return True
        return False

class CharacterClass(State):
    """
    state for character classes like [a-z0-9]
    """
    next_states: List[State] = []

    def __init__(self, class_definition: str):
        self.next_states = []
        self.chars = set()
        self._parse_class(class_definition)

    def _parse_class(self, definition: str):
        """
        Parse the character class definition
        """
        i = 0
        while i < len(definition):
            if i + 2 < len(definition) and definition[i+1] == '-':
                start_char = definition[i]
                end_char = definition[i+2]
                for char_code in range(ord(start_char), ord(end_char) + 1):
                    self.chars.add(chr(char_code))
                i += 3
            else:
                self.chars.add(definition[i])
                i += 1

    def check_self(self, char: str) -> bool:
        return char in self.chars

class RegexFSM:
    """
    Finite State Machine for regex matching."""
    def __init__(self, regex_expr: str) -> None:
        self.pattern = regex_expr
        self.curr_state = StartState()
        self.start_state = self.curr_state
        self.final_state = TerminationState()
        self.states_map = {}
        self.states_map[self.start_state] = {"transitions": {}, "epsilon": set()}
        self.states_map[self.final_state] = {"transitions": {}, "epsilon": set()}
        self._compile(regex_expr)

    def _compile(self, pattern: str):
        """
        Convert the regex pattern to a state machine.
        """
        if not pattern:
            self._add_epsilon_transition(self.start_state, self.final_state)
            return
        current_state = self.start_state
        i = 0
        while i < len(pattern):
            char = pattern[i]
            if char == '[':
                class_end = pattern.find(']', i)
                if class_end == -1:
                    raise ValueError("Unclosed character class")
                class_def = pattern[i+1:class_end]
                if class_end + 1 < len(pattern) and pattern[class_end + 1] in ('*', '+'):
                    repeat_type = pattern[class_end + 1]
                    next_state = self._handle_repetition(current_state, CharacterClass(class_def),
repeat_type)
                    current_state = next_state
                    i = class_end + 2
                else:
                    next_state = CharacterClass(class_def)
                    self._add_state(next_state)
                    self._add_transition(current_state, next_state, class_def)
                    current_state = next_state
                    i = class_end + 1
            elif i + 1 < len(pattern) and pattern[i + 1] in ('*', '+'):
                repeat_type = pattern[i + 1]
                state_type = DotState if char == '.' else AsciiState
                state = state_type() if char == '.' else AsciiState(char)
                next_state = self._handle_repetition(current_state, state, repeat_type)
                current_state = next_state
                i += 2
            else:
                if char == '.':
                    next_state = DotState()
                else:
                    next_state = AsciiState(char)
                self._add_state(next_state)
                self._add_transition(current_state, next_state, char)
                current_state = next_state
                i += 1
        self._add_epsilon_transition(current_state, self.final_state)

    def _handle_repetition(self, current_state, base_state, repeat_type):
        """
        Handle repetition operators (* and +)
        """
        self._add_state(base_state)
        if repeat_type == '*':
            loop_state = StarState(base_state)
            self._add_state(loop_state)
            self._add_epsilon_transition(current_state, loop_state)
            self._add_transition(current_state, base_state, '')
            self._add_epsilon_transition(base_state, loop_state)
            self._add_epsilon_transition(loop_state, base_state)
            return loop_state
        else:
            loop_state = PlusState(base_state)
            self._add_state(loop_state)
            self._add_transition(current_state, base_state, '')
            self._add_epsilon_transition(base_state, loop_state)
            self._add_epsilon_transition(loop_state, base_state)
            return loop_state

    def _add_state(self, state):
        if state not in self.states_map:
            self.states_map[state] = {"transitions": {}, "epsilon": set()}

    def _add_transition(self, from_state, to_state, char):
        if char not in self.states_map[from_state]["transitions"]:
            self.states_map[from_state]["transitions"][char] = set()
        self.states_map[from_state]["transitions"][char].add(to_state)
        from_state.next_states.append(to_state)

    def _add_epsilon_transition(self, from_state, to_state):
        self.states_map[from_state]["epsilon"].add(to_state)
        from_state.next_states.append(to_state)

    def __init_next_state(self, next_token: str, prev_state: State, tmp_next_state: State) -> State:
        """
        Factory method to create appropriate state for a token
        """
        new_state = None
        match next_token:
            case next_token if next_token == ".":
                new_state = DotState()
            case next_token if next_token == "*":
                new_state = StarState(tmp_next_state)
            case next_token if next_token == "+":
                new_state = PlusState(tmp_next_state)
            case next_token if next_token.isascii():
                new_state = AsciiState(next_token)
            case _:
                raise AttributeError("Character is not supported")
        self._add_state(new_state)
        return new_state

    def _epsilon_closure(self, states):
        """Find all states reachable through epsilon transitions"""
        closure = set(states)
        stack = list(states)

        while stack:
            state = stack.pop()
            for next_state in self.states_map[state]["epsilon"]:
                if next_state not in closure:
                    closure.add(next_state)
                    stack.append(next_state)
        return closure

    def check_string(self, text: str) -> bool:
        """
        Check if the input string contains the regex pattern.
        """
        if self.is_full_match(text):
            return True
        for start_pos in range(len(text)):
            current_states = self._epsilon_closure({self.start_state})
            for i in range(start_pos, len(text)):
                char = text[i]
                next_states = set()
                for state in current_states:
                    for c, destinations in self.states_map[state]["transitions"].items():
                        state_obj = next(iter([s for s in [state] if isinstance(s,
(AsciiState, DotState, CharacterClass, StarState, PlusState))]), None)
                        if c == '.' or (state_obj and isinstance(state_obj, DotState)):
                            next_states.update(destinations)
                        elif (c == char or
                              (state_obj and isinstance(state_obj, AsciiState)
and state_obj.curr_sym == char) or
                              (state_obj and isinstance(state_obj, CharacterClass)
and char in state_obj.chars)):
                            next_states.update(destinations)
                        elif state_obj and isinstance(state_obj,
(StarState, PlusState)) and state_obj.check_self(char):
                            next_states.update(destinations)
                current_states = self._epsilon_closure(next_states)
                if not current_states:
                    break
                if self.final_state in current_states:
                    return True
        return False

    def is_full_match(self, text: str) -> bool:
        """
        Check if the entire input string matches the regex pattern.
        """
        current_states = self._epsilon_closure({self.start_state})
        for char in text:
            next_states = set()
            for state in current_states:
                for c, destinations in self.states_map[state]["transitions"].items():
                    if isinstance(state, DotState):
                        next_states.update(destinations)
                    elif isinstance(state, AsciiState) and state.curr_sym == char:
                        next_states.update(destinations)
                    elif isinstance(state, CharacterClass) and char in state.chars:
                        next_states.update(destinations)
                    elif c == char:
                        next_states.update(destinations)
                    elif c == '.':
                        next_states.update(destinations)
                for next_state in state.next_states:
                    if next_state.check_self(char):
                        next_states.add(next_state)
            current_states = self._epsilon_closure(next_states)
            if not current_states:
                return False
        return self.final_state in current_states or any(state.is_final if
hasattr(state, 'is_final') else False for state in current_states)


# Test the implementation
if __name__ == "__main__":

    regex_pattern = "a*4.+hi"
    regex_compiled = RegexFSM(regex_pattern)

    print(regex_compiled.check_string("aaaaaa4uhi"))  # True
    print(regex_compiled.check_string("4uhi"))        # True
    print(regex_compiled.check_string("meow"))        # False

    print("\nAdditional tests for character class:")

    # [0-9]+
    regex_compiled = RegexFSM("[0-9]+")
    print(regex_compiled.check_string("123"))         # True
    print(regex_compiled.check_string("abc"))         # False
    print(regex_compiled.check_string("a12b"))        # False

    # [a-z0-9]+
    regex_compiled = RegexFSM("[a-z0-9]+")
    print(regex_compiled.check_string("hello123"))    # True
    print(regex_compiled.check_string("HELLO"))       # False
    print(regex_compiled.check_string("hello_world")) # False
