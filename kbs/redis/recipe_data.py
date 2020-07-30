"""Тут расположены псевдоданные рецепта """

# dough chain_id: plan_time
dough = {1: 10,
         2: 5,
         3: 10,
         4: 10,
         5: 12,
         6: 7,
         7: 2,
         }

# sauce sauce_id:{}
sauce = {2: {"duration": 20,
             "content": {
                 1: {"program": 1,
                     "sauce_station": None,
                     "qt": None,
                     },
                 2: {"program": 3,
                     "sauce_station": None,
                     "qt": None,
                     }
             }
             },
         3: {"duration": 20,
             "content": {
                 5: {"program": 7,
                     "sauce_station": None,
                     "qt": None,
                     },
             }
             }
         }

# filling -> {filling_id: {filling}
#                         dough_id_2:{filling}
#                         }

# make_crust_program \ cooking_program -> {dough_id :(heating_program_id : duration)}
filling = {1: {"cutting_program": ({"program_id": 2, "duration": 10},
                                   {"program_id": 1, "duration": 10},
                                   {"program_id": 5, "duration": 10},
                                   {"program_id": 8, "duration": 10},
                                   {"program_id": 4, "duration": 10},
                                   {"program_id": 9, "duration": 10}),
               "pre_heating_program": {1: 1, 2: 1, 3: 1, 4: 1},
               "cooking_program": {1: (1, 180), 2: (2, 180), 3: (1, 180), 4: (1, 180)},
               "stand_by_program": {1: 2, 2: 2, 3: 2, 4: 2},
               "make_crust_program": {1: (1, 20), 2: (2, 20), 3: (1, 25), 4: (1, 37)},
               }
           }

filling_chain = []

# additive chain_id: plan_time
additive = {1: 5}

recipe_data = {
    "dough": dough,
    "sauce": sauce,
    "filling": filling,
    "additive": additive
}
