import Item from '../Item/Item';
import {  Button, View } from 'react-native';
import { useState } from 'react';

const ShoppingList = ({ name, items }) => {

    const [displayList, setDisplayList] = useState(false)

    items = items.map((item) => (
        <Item
            key={item.id}
            name={item.name}
            amount={item.amount}
            bought={item.bought}
        />
    ))
    return (
        <View>
            <Button title={name} onPress={() => setDisplayList(!displayList)} />
                {displayList && items}
        </View>
    )
}

export default ShoppingList;