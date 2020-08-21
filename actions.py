from typing import Any, Text, Dict, List, Optional, Tuple

from rasa_sdk import Action, Tracker
from rasa_sdk.forms import FormAction, REQUESTED_SLOT, logger
from rasa_sdk.events import AllSlotsReset, EventType, SlotSet
from rasa_sdk.executor import CollectingDispatcher

from sqlalchemy import create_engine, Table
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# PIZZA_SIZES = ["duża", "średnia", "mała"]

Base = declarative_base()
engine = create_engine("sqlite:///study_fields.db", echo=True)


class StudyFields(Base):
    __table__ = Table('study_fields', Base.metadata, autoload=True, autoload_with=engine)


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def _get_study_fields_names() -> List:
    """get study fields from db"""
    session = Session()
    study_fields_tuples = session.query(StudyFields.name).distinct()
    study_fields_list = [x[0] for x in study_fields_tuples]
    session.close()
    print(study_fields_list)
    return study_fields_list


def _get_study_cycles(study_field_name: Text) -> List:
    """get cycles of study for specific field of study"""
    session = Session()
    study_cycles_tuples = session.query(StudyFields.cycle).filter_by(name=study_field_name).distinct()
    study_cycles_list = [x[0] for x in study_cycles_tuples]
    session.close()
    return study_cycles_list


def _get_limit_of_students(study_field, study_cycle, form_of_study) -> int:
    session = Session()
    limit_of_students = session.query(StudyFields.limit_of_students).filter_by(name=study_field,
                                                                               cycle=study_cycle,
                                                                               form_of_study=form_of_study
                                                                               ).first()
    print("limit of students type: ")
    type(limit_of_students)
    return limit_of_students[0]


def _get_study_cycles_buttons(study_field_name: Text) -> Tuple[List, List]:
    study_cycles_list = _get_study_cycles(study_field_name)
    buttons = []
    for cycle in study_cycles_list:
        study_cycle = cycle
        payload = "/inform{\"study_cycle\": \"" + study_cycle + "\"}"

        buttons.append(
            {"title": f"{study_cycle.title()}",
             "payload": payload})
    return buttons, study_cycles_list


class ShowFieldsOfStudies(Action):
    """This action retrieves pizza types (later from the db) and displays
    it to the user"""

    def name(self) -> Text:
        return "show_study_fields"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        study_fields = _get_study_fields_names()
        dispatcher.utter_message("Lista kierunków do wyboru: \n-" + "\n-".join(study_fields))
        return []


class ShowStudentsLimitForm(FormAction):
    """Form action to fill all slots required to show limits of students"""

    def name(self) -> Text:
        return "students_limit_form"

    @staticmethod
    def required_slots(tracker: "Tracker") -> List[Text]:
        """A list of required slots the form has to fill"""

        return ["study_field", "study_cycle", "form_of_study"]

    def request_next_slot(
            self,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: Dict[Text, Any],
    ) -> Optional[List[EventType]]:
        for slot in self.required_slots(tracker):
            if self._should_request_slot(tracker, slot):
                if slot == "study_cycle":
                    study_field = tracker.get_slot("study_field")
                    buttons_list, cycles_values_list = _get_study_cycles_buttons(study_field)
                    if len(cycles_values_list) > 1:
                        dispatcher.utter_button_message(text="Wybierz stopień studiów:", buttons=buttons_list)
                        return [SlotSet("study_cycle", slot)]
                    elif len(cycles_values_list) == 1:
                        return [SlotSet("study_cycle", cycles_values_list[0])]

                if slot == "form_of_study":
                    dispatcher.utter_message(template="utter_ask_form_of_study")
                    return [SlotSet("form_of_study", slot)]

                # For all other slots, continue as usual
                logger.debug(f"Request next slot '{slot}'")
                dispatcher.utter_message(
                    template=f"utter_ask_{slot}", **tracker.slots
                )
                return [SlotSet(REQUESTED_SLOT, slot)]
        return None

    def submit(
            self,
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Once required slots are filled, print message with slots values"""

        study_field = tracker.get_slot("study_field")
        study_cycle = tracker.get_slot("study_cycle")
        form_of_study = tracker.get_slot("form_of_study")

        limit = _get_limit_of_students(study_field, study_cycle, form_of_study)

        dispatcher.utter_message(f"Limit studentow na kierunku {study_field}, stopień {study_cycle} {form_of_study} "
                                 f"wynosi {limit}")
        return [AllSlotsReset()]
