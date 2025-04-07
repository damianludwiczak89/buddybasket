import { Text, SafeAreaView, Button } from 'react-native';
import React, { useState, useEffect} from 'react';
import apiInstance from '../../utils/axios';
import { Routes } from '../../navigation/Routes';
import { useNavigation } from '@react-navigation/native';
import { useFocusEffect } from '@react-navigation/native';
import ShoppingList from '../../components/ShoppingList/ShoppingList';
import { useRefreshStore } from '../../store/auth';

const Lists = () => {

    const refreshToken = useRefreshStore(state => state.refreshToken);

    const navigation = useNavigation();

    const [drafts, setDrafts] = useState([]);

    const getDrafts = async () => {
        try {
          const response = await apiInstance.get('draft/');
          console.log('Drafts:', response.data);
          setDrafts(response.data);
        } catch (error) {
          console.error(error)
          console.error('Error fetching drafts:', error.response ? error.response.data : error.message);
        }
      };

  useEffect(() => {
          getDrafts();
      }, [refreshToken])

    const lists = drafts.map((list) => (
            <ShoppingList
              id={list.id}
              key={list.id}
              name={list.name}
              items={list.items}
              active={false}
              update={getDrafts} />
          ));

  return (
    <SafeAreaView>
        <Text>Your Lists</Text>
        { lists }
        <Button title="Add New List" onPress={() => navigation.navigate(Routes.ShoppingListForm)} />
    </SafeAreaView>
  );
}

export default Lists;

//<SafeAreaView>
//<Text>Lists here</Text>
//{formDisplay && <ShoppingListForm updateLists={getLists} />}
//<Button title={formButtonTitle} onPress={() => toggleForm()} /> 
//</SafeAreaView>
//);